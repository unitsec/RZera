#!/bin/bash

export NEUTRODRPATH="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f $NEUTRODRPATH/python/__init__.py ]; then
    export PYTHONPATH="$NEUTRODRPATH/python:$PYTHONPATH"
fi
