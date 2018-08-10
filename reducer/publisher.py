from time import sleep
import json
import logging
import os
import pika
import psycopg2
import random
import socket

FNAME=os.path.basename(__file__)
PID=os.getpid()
HOST=socket.gethostname()

# set up logging
log_filename='publisher_{}.log'.format(os.getpid())
log_format = '%(levelname)s %(asctime)s {pid} {filename} %(lineno)d %(message)s'.format(
        pid=PID, filename=FNAME)
logging.basicConfig(format=log_format,
    filename='/var/log/reducerlogs/{}'.format(log_filename),
    datefmt='%Y-%m-%dT%H:%M:%S%z',
    level=logging.INFO)
logger = logging.getLogger('publisher')

try:
    DROPLET_NAME = os.environ['DROPLET_NAME']
    DB_NAME = os.environ.get('DB_NAME', 'nlp')
    DB_PASSWORD = os.environ.get('DB_PASS', '')
    DB_USER = os.environ.get('DB_USER', DB_NAME)
    JOB_ID = os.environ['JOB_ID']
    JOB_NAME = os.environ['JOB_NAME']
    MAX_QUEUE_LEN = int(os.environ.get('MAX_QUEUE_LEN', 500))
    PRE_REDUCTIONS_BASE = os.environ['PRE_REDUCTIONS_QUEUE_BASE']
    PRE_REDUCTIONS_QUEUE = PRE_REDUCTIONS_BASE + '_' + JOB_NAME
    RABBIT = os.environ.get('RABBITMQ_LOCATION', 'localhost')
except KeyError as e:
    logger.critical("important environment variables were not set")
    raise Exception('Warning: Important environment variables were not set')


def reduce_and_queue_sentences(cursor, connection, channel, start_id, limit=1000):
    """
    Pulls sentences from database starting at start_id, up to a max of limit
    Reduces then queues those sentences

    Returns the max ID of the selected sentences, or None if no sentences were returned.
    """

    cursor.execute("SELECT data->>'text', id FROM nlpdata WHERE setname='gutenberg' and typename='sentence' and id>={} ORDER BY id LIMIT {}".format(start_id, limit))

    some_pre_reductions_not_queued = True
    max_id = None
    while some_pre_reductions_not_queued:
        messages = []
        some_pre_reductions_not_queued = False
        for row in cursor.fetchmany(MAX_QUEUE_LEN):
            some_pre_reductions_not_queued = True # at least one row
            sent_str = row[0]
            channel.basic_publish(exchange='', routing_key=PRE_REDUCTIONS_QUEUE,
                    body=json.dumps(sent_str))
            messages.append('queued pre-reduction')
            max_id = row[1] if row[1] > max_id else max_id
        for message in messages:
            logger.info(message)
        q = channel.queue_declare(queue=PRE_REDUCTIONS_QUEUE)
        q_len = q.method.message_count
        while q_len > MAX_QUEUE_LEN:
            sleep(.1) # max speed w sleep (1) is MAX_QUEUE_LEN / s
            logger.info('pre reductions queue at capacity, sleeping')
            q = channel.queue_declare(queue=PRE_REDUCTIONS_QUEUE)
            q_len = q.method.message_count
    return max_id


# #Steps
#
# 1. Connect to the database
# 2. Start adding sentences to PRE_REDUCTIONS_QUEUE

# start_id determines the minimum ID of the sentences we reduce

def main(start_id=0):
    # Connect to the database
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host='localhost')
    cur = conn.cursor()

    # Check if a publisher is already running for this job, if so exit, if not
    # mark that one is running then continue.
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{reduction_publisher}', %s)
                    WHERE NOT(data ? 'reduction_publisher')
                    AND id=%s
                """, (json.dumps(DROPLET_NAME),JOB_ID))
    conn.commit()
    cur.execute("""SELECT COUNT(*) FROM nlpjobs WHERE
                    data->'reduction_publisher'=%s
                    AND id=%s
                """,
            (json.dumps(DROPLET_NAME), JOB_ID))
    continue_running = cur.fetchone()[0] == 1
    if not continue_running:
        logger.info('job already has dedicated pre-reductions publisher, exiting')
        raise Exception('This job already has a dedicated pre-reduction publisher. Exiting')

    # Connect to pika
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT))
    channel = connection.channel()

    # Declare queue if doesn't exist, get reference to queue
    q = channel.queue_declare(queue=PRE_REDUCTIONS_QUEUE)
    q_len = q.method.message_count


    # Reduce sentences from database in successive batches
    while start_id is not None:
        start_id = reduce_and_queue_sentences(cur, connection, channel, logger, start_id=start_id+1, limit=1000)
        logger.info("Reduced and queued sentences up to ID ".format(start_id))


    # update state to pre-reductions-queued
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{state}', %s)
                    WHERE id=%s
                """, (json.dumps('pre-reductions-queued'),JOB_ID))
    conn.commit()
    logger.info('all pre-reductions have been queued. waiting for acks')

    # wait until all messages have been acked
    q = channel.queue_declare(queue=PRE_REDUCTIONS_QUEUE)
    q_len = q.method.message_count
    while q_len > 0:
        sleep(2)
        q = channel.queue_declare(queue=PRE_REDUCTIONS_QUEUE)
        q_len = q.method.message_count

    logger.info('all pre-reductions have been acked. setting state to reduced.')

    # update state to reduced
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{state}', %s)
                    WHERE id=%s
                """, (json.dumps('reduced'),JOB_ID))
    conn.commit()

    logger.info('exiting')
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
