from caendr.models.sql import db, DictSerializable

class Strain(DictSerializable, db.Model):
    __tablename__ = "strain"
    species_id_method = db.Column(db.String(50), nullable=True)
    species = db.Column(db.String(50), index=True)
    isotype_ref_strain = db.Column(db.Boolean(), index=True)
    strain = db.Column(db.String(25), primary_key=True)
    isotype = db.Column(db.String(25), index=True, nullable=True)
    previous_names = db.Column(db.String(100), nullable=True)
    sequenced = db.Column(db.Boolean(), index=True, nullable=True)  # Is whole genome sequenced [WGS_seq]
    
    release = db.Column(db.Integer(), nullable=False, index=True)
    source_lab = db.Column(db.String(), nullable=True)
    
    latitude = db.Column(db.Float(), nullable=True)
    longitude = db.Column(db.Float(), nullable=True)
    landscape = db.Column(db.String(), nullable=True)
    locality_description = db.Column(db.String(), nullable=True)

    substrate = db.Column(db.String(), nullable=True)
    substrate_comments = db.Column(db.String(), nullable=True)
    substrate_temp = db.Column(db.Float())
    ambient_temp = db.Column(db.Float())
    ambient_humidity = db.Column(db.Float())
    
    associated_organism = db.Column(db.String(), nullable=True)
    inbreeding_status = db.Column(db.String(), nullable=True)
        
    sampled_by = db.Column(db.String(), nullable=True)
    isolated_by = db.Column(db.String(), nullable=True)
    sampling_date = db.Column(db.Date(), nullable=True)
    sampling_date_comment = db.Column(db.String(), nullable=True)
    notes = db.Column(db.String(), nullable=True)
    strain_set = db.Column(db.String(), nullable=True)
    issues = db.Column(db.Boolean(), nullable=True)
    issue_notes = db.Column(db.String(), nullable=True)

    # Elevation is added in and computed separately
    elevation = db.Column(db.Float(), nullable=True)

    def __repr__(self):
        return self.strain

    def to_json(self):
        return {k: v for k, v in self._asdict().items() if not k.startswith("_")}

    def strain_photo_url(self):
        # Checks if photo exists and returns URL if it does
        try:
            return check_blob(f"{STRAIN_PHOTO_PATH}{self.strain}.jpg").public_url
        except AttributeError:
            return None

    def strain_thumbnail_url(self):
        # Checks if thumbnail exists and returns URL if it does
        try:
            return check_blob(f"{STRAIN_PHOTO_PATH}{self.strain}.thumb.jpg").public_url
        except AttributeError:
            return None

    def strain_bam_url(self):
        """
            Return bam / bam_index url set
        """
        bam_file=self.strain + '.bam'
        bai_file=self.strain + '.bam.bai'
        bam_download_link = url_for('data.download_bam_url', blob_name=bam_file)
        bai_download_link = url_for('data.download_bam_url', blob_name=bai_file)
        url_set = Markup(f"""
                        <a href="{ bam_download_link }" target="_blank">
                            BAM
                        </a>
                        /
                        <a href="{ bai_download_link }" target="_blank">
                            bai
                        </a>
                   """.strip())
        return url_set

    @classmethod
    def strain_sets(cls):
        df = pd.read_sql_table(cls.__tablename__, db.engine)
        result = df[['strain', 'isotype', 'strain_set']].dropna(how='any') \
                                             .groupby('strain_set') \
                                             .agg(list) \
                                             .to_dict()
        return result['strain']


    def isotype_bam_url(self):
        """
            Return bam / bam_index url set
        """
        bam_file=self.isotype + '.bam'
        bai_file=self.isotype + '.bam.bai'
        bam_download_link = url_for('data.download_bam_url', blob_name=bam_file)
        bai_download_link = url_for('data.download_bam_url', blob_name=bai_file)
        url_set = Markup(f"""
                        <a href="{ bam_download_link }" target="_blank">
                            BAM
                        </a>
                        /
                        <a href="{ bai_download_link }" target="_blank">
                            bai
                        </a>
                   """.strip())
        return url_set

    @classmethod
    def cum_sum_strain_isotype(cls):
        """
            Create a time-series plot of strains and isotypes collected over time

            Args:
                df - the strain dataset
        """
        df = pd.read_sql_table(cls.__tablename__, db.engine)
        # Remove strains with issues
        df = df[df["issues"] == False]
        cumulative_isotype = df[['isotype', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                             .drop_duplicates(['isotype']) \
                                                             .groupby(['sampling_date'], as_index=True) \
                                                             .count() \
                                                             .cumsum() \
                                                             .reset_index()
        cumulative_isotype = cumulative_isotype.append({'sampling_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                        'isotype': len(df['isotype'].unique())}, ignore_index=True)
        cumulative_strain = df[['strain', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                           .drop_duplicates(['strain']) \
                                                           .dropna(how='any') \
                                                           .groupby(['sampling_date']) \
                                                           .count() \
                                                           .cumsum() \
                                                           .reset_index()
        cumulative_strain = cumulative_strain.append({'sampling_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                      'strain': len(df['strain'].unique())}, ignore_index=True)
        df = cumulative_isotype.set_index('sampling_date') \
                               .join(cumulative_strain.set_index('sampling_date')) \
                               .reset_index()
        return df
        

    @classmethod
    def release_summary(cls, release):
      """
          Returns isotype and strain count for a data release.

          Args:
              release - the data release
      """
      release = int(release)
      strain_count = cls.query.filter((cls.release <= release) & (cls.issues == False)).count()
      strain_count_sequenced = cls.query.filter((cls.release <= release) & (cls.issues == False) & (cls.sequenced == True)).count()
      isotype_count = cls.query.with_entities(cls.isotype).filter((cls.isotype != None), (cls.release <= release), (cls.issues == False)).group_by(cls.isotype).count()
      
      return {
        'strain_count': strain_count,
        'strain_count_sequenced': strain_count_sequenced,
        'isotype_count': isotype_count
      }

    def as_dict(self):
      return {c.name: getattr(self, c.name) for c in self.__table__.columns}


