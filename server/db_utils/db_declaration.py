from peewee import *



class Danmu(Model):
    uid = IntegerField()
    username = TextField()
    timestamp = IntegerField()
    content = TextField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

class LiveStatus(Model):
    timestamp = IntegerField()
    action = TextField()

class Gift(Model):
    uid = IntegerField()
    username = TextField()
    timestamp = IntegerField()
    gift_coin_type = TextField(null=True)
    gift_name = TextField(null=True)
    gift_num = IntegerField(null=True)
    gift_price = IntegerField(null=True)
    gift_total_price = IntegerField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

class SuperChat(Model):
    uid = IntegerField()
    username = TextField()
    timestamp = IntegerField()
    superchat_content = TextField(null=True)
    superchat_price = IntegerField(null=True)
    medal_name = TextField(null=True)
    medal_level = IntegerField(null=True)
    captain = IntegerField(null=True)

class Captain(Model):
    uid = IntegerField()
    username = TextField()
    timestamp = IntegerField()
    captain = IntegerField(null=True)
    captain_num = IntegerField(null=True)
    captain_total_price = IntegerField(null=True)

class View(Model):
    timestamp = IntegerField()
    view = IntegerField()

class WatchedChange(Model):
    timestamp = IntegerField()
    watched = IntegerField()

class Danmu2(Danmu):
    class Meta:
        schema = "merry"
        table_name = "danmu"

class LiveStatus2(LiveStatus):
    class Meta:
        schema = "merry"
        table_name = "livestatus"

class Gift2(Gift):
    class Meta:
        schema = "merry"
        table_name = "gift"

class SuperChat2(SuperChat):
    class Meta:
        schema = "merry"
        table_name = "superchat"

class Captain2(Captain):
    class Meta:
        schema = "merry"
        table_name = "captain"

class View2(Model):
    class Meta:
        schema = "merry"
        table_name = "view"

class WatchedChange2(Model):
    class Meta:
        schema = "merry"
        table_name = "watchedchange"