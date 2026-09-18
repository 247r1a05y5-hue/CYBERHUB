"""Pre-flight check: find unprocessed Phase 2 discovery records for E2E test.

Uses psycopg2 directly to avoid SQLAlchemy engine startup and async greenlet issues.
"""
import os
import re
import sys


def get_db_params():
    """Build DB connection params — prefer individual POSTGRES_* vars over URL parsing."""
    # Prefer explicit vars (avoids regex issues with special chars in password)
    host = os.environ.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT")
    dbname = os.environ.get("POSTGRES_DB")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")

    if host and user and password:
        return {
            "host": host,
            "port": int(port) if port else 5432,
            "dbname": dbname or "cyberhub",
            "user": user,
            "password": password,
        }

    # Fall back to DATABASE_URL parsing
    url = os.environ.get("DATABASE_URL", "")
    if url:
        m = re.match(
            r"postgresql(?:\+\w+)?://([^:]+):(.+)@([^:/]+):?(\d*)/(\S+)", url
        )
        if m:
            return {
                "user": m.group(1),
                "password": m.group(2),
                "host": m.group(3),
                "port": int(m.group(4)) if m.group(4) else 5432,
                "dbname": m.group(5),
            }

    raise RuntimeError("Cannot determine DB credentials from env. Set POSTGRES_HOST/USER/PASSWORD.")


def main():
    # Load .env files — root .env has real Docker credentials, backend/.env may be stale
    try:
        from dotenv import load_dotenv
        # Load root .env first (real Docker credentials)
        root_env = "/mnt/c/Users/vaish/Music/cyber security/.env"
        backend_env = "/mnt/c/Users/vaish/Music/cyber security/backend/.env"
        loaded1 = load_dotenv(root_env, override=False)
        loaded2 = load_dotenv(backend_env, override=False)
        print(f"dotenv: root={loaded1}, backend={loaded2}")
    except ImportError:
        print("python-dotenv not available")

    import psycopg2

    params = get_db_params()
    # Use POSTGRES_HOST if explicitly provided, else fallback to localhost/postgres
    params["host"] = os.environ.get("POSTGRES_HOST") or params.get("host") or "postgres"
    # Also fix stale backend/.env user/db if they snuck through
    if params.get("user") == "cyberhub" or params.get("dbname") == "cyberhub":
        print("NOTE: backend/.env creds mismatch container — using container creds directly")
        params.update({"dbname": "cyberplatform", "user": "cyberuser", "password": "cyberpass_changeme"})
    masked = {k: ("***" if k == "password" else v) for k, v in params.items()}
    print(f"Resolved params: {masked}")
    print(f"Connecting to {params['host']}:{params['port']}/{params['dbname']} ...")

    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM search_results")
        total = cur.fetchone()[0]
        print(f"Total SearchResult records: {total}")

        cur.execute("""
            SELECT COUNT(*) FROM search_results sr
            LEFT JOIN page_investigations pi ON pi.search_result_id = sr.id
            WHERE pi.id IS NULL
        """)
        unprocessed = cur.fetchone()[0]
        print(f"Unprocessed (no page_investigation): {unprocessed}")

        cur.execute("""
            SELECT sr.id, sr.page_url, sr.case_id
            FROM search_results sr
            LEFT JOIN page_investigations pi ON pi.search_result_id = sr.id
            WHERE pi.id IS NULL
            LIMIT 3
        """)
        rows = cur.fetchall()
        for r in rows:
            url_preview = str(r[1])[:80] if r[1] else "N/A"
            print(f"  Sample -> id={r[0]}  case={r[2]}  url={url_preview}")

        cur.close()
        conn.close()

        if unprocessed == 0:
            print("\nWARNING: All discovery records already investigated.")
            print("E2E test will hit idempotent-skip trap. Need a fresh record.")
            sys.exit(2)
        else:
            print(f"\nOK: {unprocessed} unprocessed records available for E2E test.")
            sys.exit(0)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
