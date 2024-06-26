from typing import List
from fastapi import FastAPI

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from web_api import router

########################################################
# start server  
print(os.getcwd())
app = FastAPI()
app.include_router(router.router)