class TintometricoRouter:
    """
    Roteador inteligente para separar as tabelas do Tintométrico e do RH do banco principal.
    """
    def db_for_read(self, model, **hints):
        if model._meta.model_name == 'pontoeletronico':
            return 'rh_db'
        if model._meta.model_name == 'usuarios': # Adicione isto
            return 'default'
        if model._meta.model_name == 'relacaoembalagenstintometrico':
            return 'tintometrico_db'
        return 'default'
    

    def db_for_write(self, model, **hints):
        if model._meta.model_name == 'pontoeletronico':
            return 'rh_db'
        if model._meta.model_name == 'usuarios': # Adicione isto
            return 'default'
        if model._meta.model_name == 'relacaoembalagenstintometrico':
            return 'tintometrico_db'
        return 'default'
    

    def allow_relation(self, obj1, obj2, **hints):
        # Permite o vínculo entre tabelas que moram em bancos diferentes 
        # (ex: O model 'User' que mora no default com o model 'PontoEletronico' que mora no rh_db)
        if obj1._meta.model_name in ['relacaoembalagenstintometrico', 'pontoeletronico'] or \
           obj2._meta.model_name in ['relacaoembalagenstintometrico', 'pontoeletronico']:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Direciona a criação das tabelas exatas para os seus arquivos de banco correspondentes
        if model_name == 'pontoeletronico':
            return db == 'rh_db'
        if model_name == 'relacaoembalagenstintometrico':
            return db == 'tintometrico_db'
            
        # 🔥 PROTEÇÃO EXTRA: Impede que as tabelas do Django (admin, auth) poluam os seus bancos secundários
        if db in ['rh_db', 'tintometrico_db']:
            return False
            
        return db == 'default'
    