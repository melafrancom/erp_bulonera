# Generated manually on 2026-05-09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='tax_condition',
            field=models.CharField(
                blank=True,
                choices=[('RI', 'Responsable Inscripto'), ('MONO', 'Monotributista'), ('EX', 'Exento'), ('CF', 'Consumidor Final'), ('NR', 'No Responsable')],
                default='',
                help_text='Determinada automáticamente por consulta a AFIP o ingresada manualmente',
                max_length=10,
                verbose_name='Condición IVA'
            ),
        ),
    ]
