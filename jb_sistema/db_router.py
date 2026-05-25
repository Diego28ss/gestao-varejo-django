class TintometricoRouter:
    """
    Roteador para separar a tabela do Tintométrico do banco de estoque.
    """
    def db_for_read(self, model, **hints):
        if model._meta.model_name == 'relacaoembalagenstintometrico':
            return 'tintometrico_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.model_name == 'relacaoembalagenstintometrico':
            return 'tintometrico_db'
        return 'default'

    # 🔥 A CORREÇÃO ESTÁ AQUI: Esta função autoriza o vínculo entre os dois bancos!
    def allow_relation(self, obj1, obj2, **hints):
        # Se um dos objetos envolvidos for a nossa tabela de amarração, nós permitimos!
        if obj1._meta.model_name == 'relacaoembalagenstintometrico' or obj2._meta.model_name == 'relacaoembalagenstintometrico':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Garante que a tabela do tintométrico só seja criada no banco correto
        if model_name == 'relacaoembalagenstintometrico':
            return db == 'tintometrico_db'
        return db == 'default'
    