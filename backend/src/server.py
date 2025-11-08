# backend/app.py
import os
import time
import jwt
import paramiko
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import dash
from dash import html, dcc
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # loads variables from backend/.env

server = Flask(__name__)


@server.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@server.get("/api/participants")
def getParticipants():
    participants = [1, 2, 3, 4, 5]
    return jsonify(participants)


@server.get("/api/participants/<participant>/dates")
def getDates(participant):
    dates = ["2023-07-10", "2023-10-10", "2023-10-13"]
    return jsonify(dates)


def runBackend():
    # set envs before running in dev if you want:
    # export JWT_SECRET="a-very-strong-secret"
    # export UNB_HOST="lambda.int.unb.ca"
    server.run(host="127.0.0.1", port=8000, debug=False)
