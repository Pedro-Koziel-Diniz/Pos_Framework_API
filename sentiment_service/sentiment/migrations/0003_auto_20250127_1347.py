# Generated by Django 3.2.25 on 2025-01-27 16:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sentiment', '0002_predictionhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='pessoa',
            name='senha',
            field=models.CharField(default='default_pass', max_length=50, verbose_name='Senha'),
        ),
        migrations.AddField(
            model_name='pessoa',
            name='usuario',
            field=models.CharField(default='default_user', max_length=50, verbose_name='Usuario'),
        ),
    ]
