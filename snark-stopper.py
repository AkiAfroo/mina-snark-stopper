#!/usr/bin/python3
# Python 3.6+
import logging
import yaml
import time
import sys
from datetime import timedelta
from CodaClient import Client


def worker_manager(mode: str):
    data = None
    if mode == "on":
        logger.info("Start worker")
        data = coda.set_current_snark_worker(WORKER_PUB_KEY, WORKER_FEE)

    elif mode == "off":
        logger.info("Turn off worker")
        data = coda.set_current_snark_worker(None, 0)
    return data


def parse_next_proposal_time():
    try:
        daemon_status = coda.get_daemon_status()
        if "startTime" not in str(daemon_status):
            next_propos = "No proposal in this epoch"
        else:
            next_propos = int(daemon_status["daemonStatus"]["nextBlockProduction"]["times"][0]["startTime"]) / 1000
        return next_propos

    except Exception as parseProposalErr:
        logger.exception(f'parse_next_proposal_time Exception: {parseProposalErr}')
        return "err"


# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='|%(asctime)s| %(message)s')
logger = logging.getLogger(__name__)
c = yaml.load(open('config.yml', encoding='utf8'), Loader=yaml.SafeLoader)
logger.info("version 1.1")
WORKER_PUB_KEY          = c["WORKER_PUB_KEY"]
WORKER_FEE              = c["WORKER_FEE"]
CHECK_PERIOD_SEC        = c["CHECK_PERIOD_SEC"]
STOP_WORKER_FOR_MIN     = c["STOP_WORKER_FOR_MIN"]
STOP_WORKER_BEFORE_MIN  = c["STOP_WORKER_BEFORE_MIN"]
GRAPHQL_HOST            = c["GRAPHQL_HOST"]
GRAPHQL_PORT            = c["GRAPHQL_PORT"]

coda = Client(graphql_host=GRAPHQL_HOST, graphql_port=GRAPHQL_PORT)
daemon_status = coda.get_daemon_status()

if type(WORKER_PUB_KEY) is not str or len(WORKER_PUB_KEY) != 55:
    try:
        WORKER_PUB_KEY = daemon_status["daemonStatus"]["snarkWorker"]
        BLOCK_PROD_KEY = daemon_status["daemonStatus"]["blockProductionKeys"][0]

        if WORKER_PUB_KEY is None:
            logger.info(f'Worker public key is None\n'
                        f'Automatically apply Block production key to {WORKER_PUB_KEY}')
            WORKER_PUB_KEY = BLOCK_PROD_KEY

        worker_manager(mode="on")
        logger.info(f'SNARK worker: {WORKER_PUB_KEY}\n'
                    f'SNARK work fee: {WORKER_FEE}')

    except Exception as workerAddrErr:
        logger.exception(f'Can\'t get worker public key. Is it running?')
        exit(1)

logger.info(f'Worker public key is: {WORKER_PUB_KEY}\n'
            f'Worker fee:           {WORKER_FEE}\n'
            f'Check period(sec):    {CHECK_PERIOD_SEC}\n'
            f'Stop before(min):     {STOP_WORKER_BEFORE_MIN}\n')

while True:
    try:
        next_proposal = parse_next_proposal_time()
        while type(next_proposal) is str:
            logger.info(next_proposal)
            time.sleep(CHECK_PERIOD_SEC)
            next_proposal = parse_next_proposal_time()

        time_to_wait = str(timedelta(seconds=int(next_proposal - time.time())))
        logger.info(f'Next proposal via {time_to_wait}')
        if next_proposal-time.time() < STOP_WORKER_BEFORE_MIN*60:
            worker_on = worker_manager(mode="off")
            logger.info(worker_on)

            logger.info(f'Waiting {STOP_WORKER_FOR_MIN} minutes')
            time.sleep(60 * STOP_WORKER_FOR_MIN)

            worker_off = worker_manager(mode="on")
            logger.info(worker_off)
        time.sleep(CHECK_PERIOD_SEC)

    except (TypeError, Exception) as parseErr:
        logger.exception(f'Parse error: {parseErr}')
        time.sleep(5)
