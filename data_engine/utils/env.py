import os
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

DEFAULT_SRC_PATH = '/Users/zhanglongbin/pythonWork/csghub-dataflow-main/demo'
RAY_ENABLE = False

def GetDataTopPath():
   # return os.environ.get("DATA_DIR", "set dir")
   return os.environ.get("DATA_DIR", DEFAULT_SRC_PATH)

def GetHubEndpoint():
    return os.environ.get("CSGHUB_ENDPOINT", "https://hub.opencsg.com")

def RayEnable():
   enalbe = os.getenv("RAY_ENABLE")
   if not enalbe:
      return RAY_ENABLE
   
   return enalbe == 'True'

def GetRayAddress():
   return os.environ.get("RAY_ADDRESS", "auto")

def OpentelemetryEnable():
   enalbe = os.getenv("ENABLE_OPENTELEMETRY")
   if not enalbe:
      return False
   
   return enalbe == 'True'