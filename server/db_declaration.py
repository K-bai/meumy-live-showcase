from peewee import *

class Danmu(Model):
    uid = IntegerField(null=True)
    username = TextField(null=True)
    timestamp = IntegerField(null=True)
    content = TextField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

    class Meta:
        table_name = 'DANMU_MSG'
        primary_key = False

class Live(Model):
    timestamp = IntegerField(null=True)
    action = TextField(null=True)

    class Meta:
        table_name = 'LIVE'
        primary_key = False

class Gift(Model):
    uid = IntegerField(null=True)
    username = TextField(null=True)
    timestamp = IntegerField(null=True)
    gift_coin_type = TextField(null=True)
    gift_name = TextField(null=True)
    gift_num = IntegerField(null=True)
    gift_price = IntegerField(null=True)
    gift_total_price = IntegerField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

    class Meta:
        table_name = 'SEND_GIFT'
        primary_key = False

class SuperChat(Model):
    uid = IntegerField(null=True)
    username = TextField(null=True)
    timestamp = IntegerField(null=True)
    superchat_content = TextField(null=True)
    superchat_price = IntegerField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

    class Meta:
        table_name = 'SUPER_CHAT_MESSAGE'
        primary_key = False

class Captain(Model):
    uid = IntegerField(null=True)
    username = TextField(null=True)
    timestamp = IntegerField(null=True)
    captain = IntegerField(null=True)
    captain_num = IntegerField(null=True)
    captain_total_price = IntegerField(null=True)


    class Meta:
        table_name = 'USER_TOAST_MSG'
        primary_key = False

class View(Model):
    timestamp = IntegerField(null=True)
    view = IntegerField(null=True)

    class Meta:
        table_name = 'VIEW'
        primary_key = False

