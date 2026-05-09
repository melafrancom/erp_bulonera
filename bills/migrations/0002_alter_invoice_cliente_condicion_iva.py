# Generated manually on 2026-05-09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bills', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='cliente_condicion_iva',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Condición IVA del cliente al emitir (RI, MONO, CF, EX, NR)',
                max_length=10
            ),
        ),
    ]
