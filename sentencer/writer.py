from psycopg2.extras import execute_values
import io
import json
import logging
import os
import pika
import psycopg2
import socket

FNAME=os.path.basename(__file__)
PID=os.getpid()
HOST=socket.gethostname()

# set up logging
log_filename='writer_{}.log'.format(os.getpid())
log_format = '%(levelname)s %(asctime)s {pid} {filename} %(lineno)d %(message)s'.format(
        pid=PID, filename=FNAME)
logging.basicConfig(format=log_format,
    filename='/var/log/sentencerlogs/{}'.format(log_filename),
    datefmt='%Y-%m-%dT%H:%M:%S%z',
    level=logging.INFO)
logger = logging.getLogger('writer')

try:
    DB_NAME = os.environ.get('DB_NAME', 'nlp')
    DB_PASSWORD = os.environ.get('DB_PASS', '')
    DB_USER = os.environ.get('DB_USER', DB_NAME)
    DROPLET_NAME = os.environ['DROPLET_NAME']
    JOB_ID = os.environ['JOB_ID']
    JOB_NAME = os.environ['JOB_NAME']
    RABBIT = os.environ.get('RABBITMQ_LOCATION', 'localhost')
    SENTENCES_BASE = os.environ['SENTENCES_QUEUE_BASE']
    SENTENCES_QUEUE = SENTENCES_BASE + '_' + JOB_NAME
    WRITER_PREFETCH_COUNT = int(os.environ.get('WRITER_PREFETCH_COUNT', 100))
except KeyError as e:
    logger.critical('important environment variables were not set')
    raise Exception('Warning: Important environment variables were not set')

# Connect to the database
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host='localhost')
cur = conn.cursor()

class LogManager():
    def __init__(self):
        self.messages = []
        self.max_len = 1000

log_mgr = LogManager()
def add_logger_info(msg):
    """Add a logger info message, write when messages reach certain length"""
    log_mgr.messages.append(msg)
    if len(log_mgr.messages) > log_mgr.max_len:
        for m in log_mgr.messages:
            logger.info(m)
        log_mgr.messages = []


class SentenceCopyManager():
    def __init__(self):
        self.argslist = []
        self.max_len = 1000

    def insert(self, sentence, job_id):
        sdata = json.dumps({'text':json.loads(sentence)})
        argslist = []
        self.argslist.append(('gutenberg','sentence',job_id, sdata))
        if len(self.argslist) >= self.max_len:
            stmt = "insert into nlpdata (setname, typename, generator, data) values %s"
            psycopg2.extras.execute_values(cur, stmt, self.argslist)
            self.argslist = []
            conn.commit()

sentence_copy_manager = SentenceCopyManager()

# #Steps:
# 1. Read sentenced strings from Sentence Queue
# 2. Write sentenced strings to database

def handle_message(ch, method, properties, body):
    try:
        body = body.decode('utf-8')
        sentence_copy_manager.insert(body, JOB_ID)
        conn.commit()
        add_logger_info('inserted sentence')
    except psycopg2.Error as e:
        logger.error('problem handling message, psycopg2 error, {}'.format(
            e.diag.message_primary))
        conn.rollback()
    except UnicodeError as e:
        logger.error("problem handling message, unicode error - {}".format(
            e))

    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    # Check if a publisher is already running for this job, if so exit, if not
    # mark that one is running then continue.
    cur.execute("""UPDATE nlpjobs SET data=jsonb_set(data, '{sentence_writer}', %s)
                    WHERE NOT(data ? 'sentence_writer')
                    AND id=%s
                """, (json.dumps(DROPLET_NAME),JOB_ID))
    conn.commit()
    cur.execute("""SELECT COUNT(*) FROM nlpjobs WHERE
                    data->'sentence_writer'=%s
                    AND id=%s
                """,
            (json.dumps(DROPLET_NAME), JOB_ID))
    continue_running = cur.fetchone()[0] == 1
    if not continue_running:
        logger.info('job has dedicated sentence writer. exiting')
        raise Exception('This job already has a dedicated sentence writer. Exiting')

    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT))
    channel = connection.channel()
    channel.queue_declare(queue=SENTENCES_QUEUE) # create queue if doesn't exist

    # NOTE: a high prefetch count is not risky here because there will only ever
    # be one writer (so this guy can't starve anyone out)
    channel.basic_qos(prefetch_count=WRITER_PREFETCH_COUNT) # limit num of unackd msgs on channel
    channel.basic_consume(handle_message, queue=SENTENCES_QUEUE, no_ack=False)
    channel.start_consuming()

    cur.close()
    conn.close()
