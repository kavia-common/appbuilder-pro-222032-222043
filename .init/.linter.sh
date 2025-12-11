#!/bin/bash
cd /home/kavia/workspace/code-generation/appbuilder-pro-222032-222043/lovable_backend_api
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

