set -e
cd "$(dirname "$0")"
DB=$1; shift
sudo -u postgres dropdb --if-exists $DB >/dev/null 2>&1
sudo -u postgres createdb $DB
for f in stub.sql stub2.sql stub3.sql; do sudo -u postgres psql -q -d $DB -f $f >/dev/null 2>&1; done
for f in "$@"; do echo "== $f"; sudo -u postgres psql -q -d $DB -v ON_ERROR_STOP=1 -f $f 2>&1 | grep -v "^NOTICE\|^psql.*NOTICE" | tail -5; done
