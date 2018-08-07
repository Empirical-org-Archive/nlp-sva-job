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
    filename='/var/log/sentencerlogs/{}'.format(log_filename),
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
    PRE_SENTENCES_BASE = os.environ['PRE_SENTENCES_QUEUE_BASE']
    PRE_SENTENCES_QUEUE = PRE_SENTENCES_BASE + '_' + JOB_NAME
    RABBIT = os.environ.get('RABBITMQ_LOCATION', 'localhost')
except KeyError as e:
    logger.critical("important environment variables were not set")
    raise Exception('Warning: Important environment variables were not set')


# #Steps
#
# 1. Connect to the database
# 2. Start adding sentences to PRE_SENTENCES_QUEUE


if __name__ == '__main__':
    # Connect to the database
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host='localhost')
    cur = conn.cursor()

    # Check if a publisher is already running for this job, if so exit, if not
    # mark that one is running then continue.
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{sentence_publisher}', %s)
                    WHERE NOT(data ? 'sentence_publisher')
                    AND id=%s
                """, (json.dumps(DROPLET_NAME),JOB_ID))
    conn.commit()
    cur.execute("""SELECT COUNT(*) FROM nlpjobs WHERE
                    data->'sentence_publisher'=%s
                    AND id=%s
                """,
            (json.dumps(DROPLET_NAME), JOB_ID))
    continue_running = cur.fetchone()[0] == 1
    if not continue_running:
        logger.info('job already has dedicated pre-sentence publisher, exiting')
        raise Exception('This job already has a dedicated sentence publisher. Exiting')

    # Issue select statements - cast to json from jsonb
    cur.execute("SELECT data->>link FROM nlpdata WHERE setname='gutenberg' and typename='booklink' ORDER BY RANDOM()")

    # Connect to pika
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT))
    channel = connection.channel()

    # Declare queue if doesn't exist, get reference to queue
    q = channel.queue_declare(queue=PRE_SENTENCES_QUEUE)
    q_len = q.method.message_count
    some_pre_sentences_not_queued = True
    while some_pre_sentences_not_queued:
        messages = []
        some_pre_sentences_not_queued = False
        for row in cur.fetchmany(MAX_QUEUE_LEN):
            some_pre_sentences_not_queued = True # at least one row
            sent_str = row[0]
            channel.basic_publish(exchange='', routing_key=PRE_SENTENCES_QUEUE,
                    body=json.dumps(sent_str))
            messages.append('queued pre-sentence')
        for message in messages:
            logger.info(message)
        q = channel.queue_declare(queue=PRE_SENTENCES_QUEUE)
        q_len = q.method.message_count
        while q_len > MAX_QUEUE_LEN:
            sleep(.1) # max speed w sleep (1) is MAX_QUEUE_LEN / s
            logger.info('pre sentences queue at capacity, sleeping')
            q = channel.queue_declare(queue=PRE_SENTENCES_QUEUE)
            q_len = q.method.message_count

    # update state to pre-sentences-queued
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{state}', %s)
                    WHERE id=%s
                """, (json.dumps('pre-sentences-queued'),JOB_ID))
    conn.commit()
    logger.info('all pre-sentences have been queued. waiting for acks')

    # wait until all messages have been acked
    q = channel.queue_declare(queue=PRE_SENTENCES_QUEUE)
    q_len = q.method.message_count
    while q_len > 0:
        sleep(2)
        q = channel.queue_declare(queue=PRE_SENTENCES_QUEUE)
        q_len = q.method.message_count

    logger.info('all pre-sentences have been acked. setting state to sentenced.')
    # update state to sentenced
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{state}', %s)
                    WHERE id=%s
                """, (json.dumps('sentenced'),JOB_ID))
    conn.commit()

    logger.info('exiting')
    cur.close()
    conn.close()
