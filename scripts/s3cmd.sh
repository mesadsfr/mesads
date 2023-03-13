#!/bin/bash

ENV_FILE=$(realpath $(dirname $0)/../.prod.env)
S3CFG_FILE=$(realpath $(dirname $0)/../.s3cfg)
REQUIRED_VARS=(AWS_S3_ENDPOINT_URL AWS_S3_ACCESS_KEY_ID AWS_S3_SECRET_ACCESS_KEY AWS_STORAGE_BUCKET_NAME)

load_env() {
    if [ ! -f "${ENV_FILE}" ];
    then
        cat<<EOF
ERROR: File $ENV_FILE is required with the following variables:
$(printf "\t%s\n" "${REQUIRED_VARS[@]}")
EOF
        exit 1
    fi

    # Load variables
    export $(grep -v '^#' "$ENV_FILE" | xargs)

    for name in ${REQUIRED_VARS[@]}; do
        if [ -z "${!name}" ];
        then
            echo "ERROR: Variable $name is required in $ENV_FILE" >&2
            exit 1
        fi
    done
}

usage() {
    echo "Usage: $0 <s3cmd args>" >&2
    echo "Example: $0 ls" >&2
    exit 1
}

load_env


cat<<EOF > "$S3CFG_FILE"
access_key = ${AWS_S3_ACCESS_KEY_ID}
secret_key = ${AWS_S3_SECRET_ACCESS_KEY}
bucket_location =
cloudfront_host =
cloudfront_resource =
default_mime_type = binary/octet-stream
delete_removed = False
dry_run = False
encoding = UTF-8
encrypt = False
follow_symlinks = False
force = False
get_continue = False
guess_mime_type = True
host_base = ${AWS_S3_ENDPOINT_URL}
host_bucket = %(bucket)s.$(echo ${AWS_S3_ENDPOINT_URL} | sed -E 's#https?://(.*)#\1#')
human_readable_sizes = False
list_md5 = False
log_target_prefix =
preserve_attrs = True
progress_meter = True
proxy_host =
proxy_port = 0
recursive = False
recv_chunk = 4096
reduced_redundancy = False
send_chunk = 4096
skip_existing = False
socket_timeout = 300
urlencoding_mode = normal
use_https = True
verbosity = WARNING
EOF

exec docker run --rm -ti -v "$S3CFG_FILE":/root/.s3cfg gdaws/s3cmd "$@"