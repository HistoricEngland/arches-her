from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("arches_her", "0011_auto_20260625_0950"),
    ]

    operations = [
        migrations.CreateModel(
            name="HeritageApiConceptMapping",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("hapi_field", models.CharField(max_length=255)),
                ("source_concept", models.CharField(max_length=255)),
                ("mandatory", models.BooleanField(default=False)),
                (
                    "heritage_gateway_concept",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            options={
                "verbose_name": "Heritage API Concept Mapping",
                "verbose_name_plural": "Heritage API Concept Mappings",
                "db_table": "hapi_concept_mapping",
                "managed": True,
            },
        ),
        migrations.AddConstraint(
            model_name="heritageapiconceptmapping",
            constraint=models.UniqueConstraint(
                fields=("hapi_field", "source_concept"),
                name="hapi_concept_mapping_hapi_field_source_concept_uniq",
            ),
        ),
    ]
