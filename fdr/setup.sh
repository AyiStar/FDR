#!/bin/bash

mysql -u ayistar  < init_database.sql
python3 init_dir.py