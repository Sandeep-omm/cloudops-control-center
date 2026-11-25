"""Create or rotate the restricted application login before running migrations."""

import os

import psycopg
from psycopg import sql


def main() -> None:
    admin_url = os.environ["DATABASE_ADMIN_URL"]
    app_password = os.environ["APP_DB_PASSWORD"]
    role_name = "cloudops_app"

    with psycopg.connect(admin_url, autocommit=True) as connection:
        role_exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (role_name,),
        ).fetchone()

        if role_exists:
            role_statement = "ALTER ROLE {} WITH LOGIN PASSWORD %s"
        else:
            role_statement = "CREATE ROLE {} WITH LOGIN PASSWORD %s"
        connection.execute(
            sql.SQL(role_statement).format(sql.Identifier(role_name)),
            (app_password,),
        )
        connection.execute(
            sql.SQL("GRANT CONNECT, CREATE, TEMPORARY ON DATABASE {} TO {}").format(
                sql.Identifier("cloudops"),
                sql.Identifier(role_name),
            )
        )
        connection.execute(
            sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                sql.Identifier(role_name),
            )
        )


if __name__ == "__main__":
    main()
