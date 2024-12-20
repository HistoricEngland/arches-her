class MonumentSource(object):
    def __init__(
        self, 
        information_source_title: str = None, 
        statement_of_authority: str = None, 
        source_no: str = None, 
        source_reference: str = None, 
        date_of_origination: str = None, 
        source_digital_object_identifier: str = None, 
        source_url: str = None
    ):
        self.informationSourceTitle = information_source_title
        self.statementOfAuthority = statement_of_authority
        self.sourceNo = source_no
        self.sourceReference = source_reference
        self.dateOfOrigination = date_of_origination
        self.sourceDigitalObjectIdentifier = source_digital_object_identifier
        self.sourceUrl = source_url

    def __str__(self):
        return f"MonumentSource(informationSourceTitle={self.informationSourceTitle}, statementOfAuthority={self.statementOfAuthority}, sourceNo={self.sourceNo}, sourceReference={self.sourceReference}, dateOfOrigination={self.dateOfOrigination}, sourceDigitalObjectIdentifier={self.sourceDigitalObjectIdentifier}, sourceUrl={self.sourceUrl})"
