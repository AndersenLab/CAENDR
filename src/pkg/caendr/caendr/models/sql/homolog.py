from caendr.models.sql import db, DictSerializable

class Homologs(DictSerializable, db.Model):
    """
        The homologs database combines
    """
    __tablename__ = "homologs"
    id = db.Column(db.Integer, primary_key=True)
    gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), nullable=True, index=True)
    gene_name = db.Column(db.String(60), index=True)
    homolog_species = db.Column(db.String(60), index=True)
    homolog_taxon_id = db.Column(db.Integer, index=True, nullable=True)  # If available
    homolog_gene = db.Column(db.String(60), index=True)
    homolog_source = db.Column(db.String(60))
    is_ortholog = db.Column(db.Boolean(), index=True, nullable=True)

    __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='homologs', lazy='joined')


    def to_json(self):
      return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


    def unnest(self):
        """
            Used with the gene API - returns
            an unnested homolog datastructure combined with the wormbase gene summary model.
        """
        self.__dict__.update(self.__gene_summary__.__dict__)
        return self

    def __repr__(self):
        return f"homolog: {self.gene_name} -- {self.homolog_gene}"

