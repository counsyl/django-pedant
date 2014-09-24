import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# This allows specifying a file DB for manual testing,
# but defaults to memory for test.
__db_file_name = os.environ.get('DBFILENAME', ':memory:')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': __db_file_name,
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SECRET_KEY = '*#^6m1-xu$k_!x-#)h30f1m2uvp65ea#jjx%0mk4#oumgzw4ld'

INSTALLED_APPS = (
    'django_nose',
    'pedant',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
