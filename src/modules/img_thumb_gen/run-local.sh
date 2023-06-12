#!/bin/bash

IMG_URI=local/img_thumb_gen

SCRIPT_PATH=$1
if [ -z "$SCRIPT_PATH" ]; then
    echo "Usage"
    echo "\$ ./run-local-script.sh PATH_TO_SCRIPT_PY"
    echo "Example:"
    echo "./run-local-script.sh ./scripts/fix_missing_thumbs.py"
    exit
fi

docker run -it \
    -v $GOOGLE_APPLICATION_CREDENTIALS:/secret \
    -v .:/img_thumb_gen \
    --env-file .env \
    --env-file module.env \
    -e GOOGLE_APPLICATION_CREDENTIALS=/secret \
    -e ENV=$ENV \
    $IMG_URI \
    python /img_thumb_gen/$SCRIPT_PATH

