import unittest
from pathlib import Path


class CoursePlatformMigrationEnumTests(unittest.TestCase):
    def test_manually_created_enums_disable_table_time_creation(self):
        migration = Path(
            "alembic/versions/20260418_course_platform_schema.py"
        ).read_text()

        create_type_false_count = migration.count("create_type=False")
        postgres_enum_count = migration.count("postgresql.ENUM(")
        self.assertGreaterEqual(
            create_type_false_count,
            10,
            "Expected course platform migration enums to set create_type=False "
            "when they are created manually before table creation.",
        )
        self.assertGreaterEqual(
            postgres_enum_count,
            10,
            "Expected course platform migration to use postgresql.ENUM so "
            "create_type=False is respected during table creation.",
        )


if __name__ == "__main__":
    unittest.main()
