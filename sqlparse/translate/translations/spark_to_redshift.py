from sqlparse.translate.translate import Translation, TranslationCommand
import sqlparse.translate.translations.rules as rules

rules = [rules.spark_cast_to_redshift]
translation = Translation('spark', 'redshift', rules)
