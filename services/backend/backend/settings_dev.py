"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 2.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '#=y$xvz9s8lvyc)z=(surr__f(27)o_q0)-vt9r&u$imq90+2e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["13.232.196.42", "dev-dash.pragyaam.in","127.0.0.1","52.66.213.162","192.168.0.110"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'app.apps.AppConfig',
    'corsheaders',
    'django_mysql',
    'django_celery_beat', 
    # "django_rq",
    'channels'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

ASGI_APPLICATION = 'backend.routing.application'

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

# DJANGO_PW = os.getenv('DJANGO_PASSWORD')
# if not DJANGO_PW:
#     try:
#         f = open('/etc/secrets/djangouserpw')
#         DJANGO_PW = f.readline().rstrip()
#     except IOError:
#         pass
# if not DJANGO_PW:
#     raise Exception("NO DJNAGO_PASSWORD provided.")

DATABASES = {
    'default' : {
        'ENGINE' : 'django.db.backends.mysql',
        'NAME' : os.environ['SQL_DATABASE'],
        'USER' : os.environ['SQL_USER'],
        'PASSWORD' : os.environ['SQL_PASSWORD'],
        'HOST' : os.environ['SQL_HOST'],
        'PORT' : os.environ['SQL_PORT'],
    },
    'rds' : {
        'ENGINE' : 'django.db.backends.mysql',
        'OPTIONS' : {
            'read_default_file' : os.path.join(BASE_DIR, 'cred.cnf'),
        }
    }
}

# RQ_QUEUES = {
#     'default' : {
#         'HOST' : '127.0.0.1',
#         'PORT' : 6379,
#         'DB' : 3,
#     }
# }

# CELERY STUFF
BROKER_URL = 'redis://127.0.0.1:6379/3'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/3'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_IGNORE_RESULT = True
CELERY_TRACK_STARTED = True
CELERY_SEND_EVENTS = True

APPEND_SLASH=False

# DATABASE_ROUTERS = ['app.routers.Router']

AUTHENTICATION_BACKENDS = (
    )


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
    )
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

CORS_ORIGIN_ALLOW_ALL = True

# ASGI_APPLICATION = 'backend.routing.application'

CHANNEL_LAYERS = {
    'default' : {
        'BACKEND' : 'channels_redis.core.RedisChannelLayer',
        'CONFIG' : {
            "hosts" : ['redis://{}/5'.format(os.environ['REDIS_URL'])]
        }
    }
}

