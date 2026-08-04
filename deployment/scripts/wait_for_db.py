import os
import sys
import time

def check_db():
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")

    try:
        import psycopg
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            connect_timeout=3
        )
        conn.close()
        return True
    except ImportError:
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=3
            )
            conn.close()
            return True
        except ImportError:
            # Fallback to pure socket check if drivers are not loaded in execution path
            import socket
            try:
                s = socket.create_connection((host, int(port)), timeout=3)
                s.close()
                return True
            except OSError:
                return False
        except Exception as e:
            print(f"Database connection attempt failed: {e}")
            return False
    except Exception as e:
        print(f"Database connection attempt failed: {e}")
        return False

def main():
    print("Checking database availability...")
    retries = 30
    while retries > 0:
        if check_db():
            print("Database is reachable and ready!")
            sys.exit(0)
        else:
            print(f"Database not reachable yet. Retrying in 1 second... ({retries} retries left)")
            time.sleep(1)
            retries -= 1
    print("Database connection timed out. Exiting.")
    sys.exit(1)

if __name__ == "__main__":
    main()
