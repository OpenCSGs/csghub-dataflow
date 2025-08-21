from data_celery.main import celery_app
from data_celery.job.tasks import run_pipline_job
from data_server.job.JobModels import Job
from data_server.database.session import get_sync_session

import time
from datetime import datetime
import pytz
if __name__ == '__main__':
    print("main")
    # #
    job_uuid = "2fef1013-81fd-480e-92d9-be692ba0c8dc"
    session = get_sync_session()
    job: Job = session.query(Job).filter(Job.uuid == job_uuid).first()
    result_pipline_job = run_pipline_job.delay(job_uuid,str(54),"z275748353","9eba3d0173eb48ed99bb6952233bbb50")
    #
    print(f"result_pipline_job ID: {result_pipline_job.id}")
    job.job_celery_uuid = result_pipline_job.id
    session.commit()
