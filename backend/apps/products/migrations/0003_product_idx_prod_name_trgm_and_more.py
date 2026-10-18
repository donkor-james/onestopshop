from django.contrib.postgres.operations import CreateExtension
from django.db import migrations
import django.contrib.postgres.indexes
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_product_idx_prod_active_created'),
    ]

    operations = [
        CreateExtension('pg_trgm'),

        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'CREATE INDEX "idx_prod_name_trgm" '
                        'ON "products_product" USING gin '
                        '((UPPER("name")) gin_trgm_ops);'
                    ),
                    reverse_sql=(
                        'DROP INDEX IF EXISTS "idx_prod_name_trgm";'
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'CREATE INDEX "idx_prod_desc_trgm" '
                        'ON "products_product" USING gin '
                        '((UPPER("description")) gin_trgm_ops);'
                    ),
                    reverse_sql=(
                        'DROP INDEX IF EXISTS "idx_prod_desc_trgm";'
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='product',
                    index=django.contrib.postgres.indexes.GinIndex(
                        django.contrib.postgres.indexes.OpClass(
                            django.db.models.functions.text.Upper('name'),
                            name='gin_trgm_ops',
                        ),
                        name='idx_prod_name_trgm',
                    ),
                ),
                migrations.AddIndex(
                    model_name='product',
                    index=django.contrib.postgres.indexes.GinIndex(
                        django.contrib.postgres.indexes.OpClass(
                            django.db.models.functions.text.Upper('description'),
                            name='gin_trgm_ops',
                        ),
                        name='idx_prod_desc_trgm',
                    ),
                ),
            ],
        ),
    ]
