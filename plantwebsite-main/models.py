from extensions import db
from datetime import datetime, date



# Core Data Models 

class ClientBusiness(db.Model):
    __tablename__ = 'client_business'
    client_business_name = db.Column(db.Text, primary_key=True, nullable=False)

    def __repr__(self):
        return f"<ClientBusiness {self.client_business_name}>"

class DataSource(db.Model):
    __tablename__ = 'data_source'
    data_source_name = db.Column(db.Text, primary_key=True, nullable=False)
    vernacular_name = db.Column(db.Text)

    def __repr__(self):
        return f"<DataSource {self.data_source_name}>"

class Family(db.Model):
    __tablename__ = 'family'
    family_name = db.Column(db.Text, primary_key=True, nullable=False)

    def __repr__(self):
        return f"<Family {self.family_name}>"

class Reserve(db.Model):
    __tablename__ = 'reserve'
    reserve_name = db.Column(db.Text, primary_key=True, nullable=False)
    reserve_type = db.Column(db.Text)
    reserve_address = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('reserve_name', name='reserve_name_unique'),
    )

    def __repr__(self):
        return f"<Reserve {self.reserve_name}>"

class Species(db.Model):
    __tablename__ = 'species'
    scientific_name = db.Column(db.Text, primary_key=True, nullable=False)
    vernacular_name = db.Column(db.Text)
    genus = db.Column(db.Text)
    subgenus = db.Column(db.Text)
    taxon_rank = db.Column(db.Text)
    family_name = db.Column(db.Text, db.ForeignKey('family.family_name'))
    exotic = db.Column(db.Boolean)
    threatened_species_status = db.Column(db.String(255))
    species_traits = db.relationship('SpeciesTraitJunction', lazy=True, backref=db.backref('species_ref', lazy=True)) # Added explicit backref name

    __table_args__ = (
        db.Index('ix_species_exotic', 'exotic'),
    )

    def __repr__(self):
        return f"<Species {self.scientific_name}>"

    def to_dict(self):
        return {
            'scientificName': self.scientific_name,
            'vernacularName': self.vernacular_name,
            'genus': self.genus,
            'subgenus': self.subgenus,
            'taxonRank': self.taxon_rank,
            'familyName': self.family_name,
            'exotic': self.exotic,
            'threatenedSpeciesStatus': self.threatened_species_status,
        }

class Traits(db.Model):
    __tablename__ = 'traits'
    trait_name = db.Column(db.Text, primary_key=True, nullable=False)
    trait_info = db.Column(db.Text)

    def __repr__(self):
        return f"<Trait {self.trait_name}>"

# Tables with Foreign Keys 

class Occurrence(db.Model):
    __tablename__ = 'occurrences'
    occurrence_id = db.Column(db.Integer, primary_key=True)
    scientific_name = db.Column(db.Text, db.ForeignKey('species.scientific_name'))
    # DEFINITIVE: Set to db.DateTime for TIMESTAMP in DB
    event_date = db.Column(db.DateTime)
    dataset_name = db.Column(db.Text)
    reserve_name = db.Column(db.Text, db.ForeignKey('reserve.reserve_name'))
    decimal_latitude = db.Column(db.Float)
    decimal_longitude = db.Column(db.Float)
    individual_count = db.Column(db.Integer)
    reproductive_condition = db.Column(db.Text)
    establishment_means = db.Column(db.Text)
    occurrence_remarks = db.Column(db.Text)
    year = db.Column(db.Integer)
    month = db.Column(db.Text)
    day = db.Column(db.Integer)
    habitat = db.Column(db.Text)
    sampling_protocol = db.Column(db.Text)
    locality = db.Column(db.Text)
    location_remarks = db.Column(db.Text)
    identified_by = db.Column(db.Text)
    date_identified = db.Column(db.Text)
    owner_institution_code = db.Column(db.Text)
    basis_of_record = db.Column(db.Text)
    data_generalizations = db.Column(db.Text)
    recorded_by = db.Column(db.Text)
    client_business_name = db.Column(db.Text, db.ForeignKey('client_business.client_business_name'))

    __table_args__ = (
        db.Index('ix_occurrences_map_filters', 'scientific_name', 'dataset_name', 'reserve_name', 'year', 'decimal_latitude', 'decimal_longitude'),
    )

    def __repr__(self):
        return f"<Occurrence {self.occurrence_id} - {self.scientific_name}>"

    def to_dict(self):
        row_dict = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name)
            if isinstance(value, (datetime, date)):
                row_dict[col.name] = value.isoformat()
            else:
                row_dict[col.name] = value
        return {
            'occurrenceId': row_dict.get('occurrence_id'),
            'scientificName': row_dict.get('scientific_name'),
            'eventDate': row_dict.get('event_date'),
            'datasetName': row_dict.get('dataset_name'),
            'reserveName': row_dict.get('reserve_name'),
            'decimalLatitude': row_dict.get('decimal_latitude'),
            'decimalLongitude': row_dict.get('decimal_longitude'),
            'individualCount': row_dict.get('individual_count'),
            'reproductiveCondition': row_dict.get('reproductive_condition'),
            'establishmentMeans': row_dict.get('establishment_means'),
            'occurrenceRemarks': row_dict.get('occurrence_remarks'),
            'year': row_dict.get('year'),
            'month': row_dict.get('month'),
            'day': row_dict.get('day'),
            'habitat': row_dict.get('habitat'),
            'samplingProtocol': row_dict.get('sampling_protocol'),
            'locality': row_dict.get('locality'),
            'locationRemarks': row_dict.get('location_remarks'),
            'identifiedBy': row_dict.get('identified_by'),
            'dateIdentified': row_dict.get('date_identified'),
            'ownerInstitutionCode': row_dict.get('owner_institution_code'),
            'basisOfRecord': row_dict.get('basis_of_record'),
            'dataGeneralizations': row_dict.get('data_generalizations'),
            'recordedBy': row_dict.get('recorded_by'),
            'clientBusinessName': row_dict.get('client_business_name'),
        }

class LocalSpeciesInfo(db.Model):
    __tablename__ = 'local_species_info'
    local_species_id = db.Column(db.Integer, primary_key=True)
    planted_native = db.Column(db.Text)
    scientific_name = db.Column(db.Text, db.ForeignKey('species.scientific_name'))
    client_business_name = db.Column(db.Text, db.ForeignKey('client_business.client_business_name'))

    __table_args__ = (
        db.Index('ix_local_species_info_map_filters', 'scientific_name', 'planted_native'),
    )

    def __repr__(self):
        return f"<LocalSpeciesInfo {self.local_species_id} - {self.scientific_name}>"

    def to_dict(self):
        return {
            'localSpeciesId': self.local_species_id,
            'plantedNative': self.planted_native,
            'scientificName': self.scientific_name,
            'clientBusinessName': self.client_business_name,
        }

class SpeciesTraitJunction(db.Model):
    __tablename__ = 'species_trait_junction'
    species_trait_junction_id = db.Column(db.Integer, primary_key=True, nullable=False)
    scientific_name = db.Column(db.Text, db.ForeignKey('species.scientific_name'))
    trait_name = db.Column(db.Text, db.ForeignKey('traits.trait_name'))
    species = db.relationship('Species', backref=db.backref('species_trait_junctions_on_species', lazy=True))
    trait = db.relationship('Traits', backref=db.backref('species_trait_junctions_on_trait', lazy=True))

    def __repr__(self):
        return f"<SpeciesTraitJunction {self.species_trait_junction_id}>"

    def to_dict(self):
        return {
            'speciesTraitJunctionId': self.species_trait_junction_id,
            'scientificName': self.scientific_name,
            'traitName': self.trait_name,
        }

class Fauna(db.Model):
    __tablename__ = 'fauna'

    fauna_id = db.Column(db.Integer, primary_key=True)
    old_location_name = db.Column(db.Text)
    genus = db.Column(db.Text)
    species = db.Column(db.Text)
    family = db.Column(db.Text)
    vernacular_name = db.Column(db.Text)
    class_name = db.Column('class', db.Text)
    rare_endangered = db.Column(db.Boolean)
    local_rare_endangered = db.Column(db.Boolean)
    exotic = db.Column(db.Boolean)
    year = db.Column(db.Integer)
    decimal_longitude = db.Column(db.Float)
    decimal_latitude = db.Column(db.Float)
    reserve_name = db.Column(db.Text, db.ForeignKey('reserve.reserve_name'))

    def to_dict(self):
        row_dict = {}
        for prop in self.__mapper__.iterate_properties:
            if hasattr(prop, 'key'):
                attr_name = prop.key
                value = getattr(self, attr_name)
                row_dict[attr_name] = value
        return row_dict

    def __repr__(self):
        return f"<Fauna {self.genus} {self.species} ({self.vernacular_name})>"