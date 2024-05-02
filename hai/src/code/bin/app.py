from typing import List
from fastapi import FastAPI

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from web_api import router, getmusic_router

########################################################
# start server
app = FastAPI()
app.include_router(router.router)