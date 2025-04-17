import os
import json

class FonteEnergia:
    """Modelo para representar uma fonte de energia solar"""
    
    def __init__(self, nome, localizacao, capacidade, marca, modelo, data_instalacao, id=None):
        self.id = id
        self.nome = nome
        self.localizacao = localizacao
        self.capacidade = float(capacidade)  # capacidade em kWp
        self.marca = marca
        self.modelo = modelo
        self.data_instalacao = data_instalacao
        
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'localizacao': self.localizacao,
            'capacidade': self.capacidade,
            'marca': self.marca,
            'modelo': self.modelo,
            'data_instalacao': self.data_instalacao
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria uma instância a partir de um dicionário"""
        return cls(
            id=data.get('id'),
            nome=data.get('nome'),
            localizacao=data.get('localizacao'),
            capacidade=data.get('capacidade'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            data_instalacao=data.get('data_instalacao')
        )
        
class FonteEnergiaRepository:
    """Repositório para persistência de fontes de energia"""
    
    FONTES_FILE = os.path.join('data', 'fontes_energia.json')
    
    @classmethod
    def salvar(cls, fonte):
        """Salva uma fonte no repositório"""
        fontes = cls.listar_todas()
        
        # Gera um novo ID se não existir
        if fonte.id is None:
            ids = [f['id'] for f in fontes if f['id'] is not None]
            fonte.id = 1 if not ids else max(ids) + 1
            
        # Atualiza ou adiciona a fonte
        for i, f in enumerate(fontes):
            if f['id'] == fonte.id:
                fontes[i] = fonte.to_dict()
                break
        else:
            fontes.append(fonte.to_dict())
            
        # Salva no arquivo
        os.makedirs(os.path.dirname(cls.FONTES_FILE), exist_ok=True)
        with open(cls.FONTES_FILE, 'w') as f:
            json.dump(fontes, f, indent=4)
            
        return fonte
    
    @classmethod
    def listar_todas(cls):
        """Lista todas as fontes cadastradas"""
        if not os.path.exists(cls.FONTES_FILE):
            return []
            
        with open(cls.FONTES_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    
    @classmethod
    def buscar_por_id(cls, id):
        """Busca uma fonte pelo ID"""
        fontes = cls.listar_todas()
        for fonte in fontes:
            if fonte['id'] == id:
                return FonteEnergia.from_dict(fonte)
        return None
        
    @classmethod
    def excluir(cls, id):
        """Exclui uma fonte pelo ID"""
        fontes = cls.listar_todas()
        fontes = [f for f in fontes if f['id'] != id]
        
        with open(cls.FONTES_FILE, 'w') as f:
            json.dump(fontes, f, indent=4)