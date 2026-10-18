# Initial native-Django migration for the standalone modernization.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='LiveChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=220, unique=True)),
                ('description', models.TextField(blank=True)),
                ('expert', models.CharField(blank=True, max_length=100)),
                ('chat_starts_at', models.DateTimeField(db_index=True)),
                ('chat_ends_at', models.DateTimeField(db_index=True)),
                ('maximum_questions', models.PositiveIntegerField(blank=True, help_text='Leave blank for no question limit; 0 closes submissions.', null=True)),
                ('comments_closed', models.BooleanField(default=False)),
                ('is_cancelled', models.BooleanField(default=False)),
                ('is_archived', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('object_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='livechat_sessions', to='contenttypes.contenttype')),
            ],
            options={'ordering': ('-chat_starts_at',), 'verbose_name': 'Live chat', 'verbose_name_plural': 'Live chats'},
        ),
        migrations.CreateModel(
            name='LiveChatQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('body', models.TextField(max_length=3000)),
                ('is_approved', models.BooleanField(default=False)),
                ('is_removed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('livechat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='livechat.livechat')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='LiveChatResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response', models.TextField(max_length=10000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('livechat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='livechat.livechat')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='livechat.livechatquestion')),
            ],
            options={'ordering': ('created_at',)},
        ),
    ]
