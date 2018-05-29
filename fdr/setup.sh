#!/bin/bash

mysql -u $1  < init_database.sql
python3 init_dir.py