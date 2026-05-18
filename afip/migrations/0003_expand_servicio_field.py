# Generated manually — expand WSAAToken.servicio from max_length=20 to 50
# and add ws_sr_constancia_inscripcion to choices.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('afip', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wsaatoken',
            name='servicio',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('wsfe', 'Facturación Electrónica v1'),
                    ('wsfe_v2', 'Facturación Electrónica v2'),
                    ('ws_sr_constancia_inscripcion', 'Constancia de Inscripción (Padrón A5)'),
                ],
            ),
        ),
    ]
