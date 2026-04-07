GET_ONTOLOGY_SCHEMA = """
MATCH (n:EntityType)
RETURN n.name AS entity_name, n.description AS description
ORDER BY n.name
"""

GET_RELATIONSHIP_TYPES = """
MATCH (r:RelationshipType)
RETURN r.name AS rel_name, r.source_types AS source_types, 
       r.target_types AS target_types, r.description AS description
ORDER BY r.name
"""

EXTRACT_ENTITIES_QUERY = """
MATCH (e:ExtractedEntity {document_id: $document_id})
RETURN e.name AS name, e.entity_type AS entity_type, 
       e.mention AS mention, e.confidence AS confidence
"""

EXTRACT_RELATIONSHIPS_QUERY = """
MATCH (e1:ExtractedEntity {document_id: $document_id})-[r:EXTRACTED_RELATIONSHIP]->(e2:ExtractedEntity)
RETURN e1.name AS source, e2.name AS target, 
       type(r) AS relationship, r.justification AS justification
"""

VALIDATE_EXTRACTION = """
MATCH (rt:RelationshipType {name: $relationship})
RETURN rt.source_types AS valid_sources, rt.target_types AS valid_targets,
       rt.is_valid AS is_valid
"""

SEED_ONTOLOGY = """
// Entity Types (Ontology Schema)
MERGE (et1:EntityType {name: "Authority"})
SET et1.description = "A person or role that has power to make decisions",
    et1.required = true

MERGE (et2:EntityType {name: "Precondition"})
SET et2.description = "A condition that must be satisfied before an action",
    et2.required = true

MERGE (et3:EntityType {name: "Obligation"})
SET et3.description = "A requirement that a party must fulfill",
    et3.required = true

MERGE (et4:EntityType {name: "ProhibitedAction"})
SET et4.description = "An action that is explicitly forbidden",
    et4.required = true

MERGE (et5:EntityType {name: "Condition"})
SET et5.description = "A conditional clause that modifies a rule",
    et5.required = false

MERGE (et6:EntityType {name: "Party"})
SET et6.description = "A person, organization or role mentioned in the text",
    et6.required = true

MERGE (et7:EntityType {name: "Action"})
SET et7.description = "An activity or task that can be performed",
    et7.required = true

// Relationship Types (Valid connections between entities)
MERGE (rt1:RelationshipType {name: "HAS_AUTHORITY"})
SET rt1.source_types = ["Party", "Authority", "Role", "User", "Employee"], rt1.target_types = ["Action", "Activity", "Task"],
    rt1.description = "Party has authority to perform an action",
    rt1.is_valid = true

MERGE (rt2:RelationshipType {name: "REQUIRES_PRECONDITION"})
SET rt2.source_types = ["Action", "Activity", "Task"], rt2.target_types = ["Precondition", "Condition", "Requirement"],
    rt2.description = "Action requires precondition to be satisfied",
    rt2.is_valid = true

MERGE (rt3:RelationshipType {name: "MUST_FULFILL"})
SET rt3.source_types = ["Party", "Authority", "Role", "User", "Employee"], rt3.target_types = ["Obligation", "Duty", "Requirement"],
    rt3.description = "Party must fulfill an obligation",
    rt3.is_valid = true

MERGE (rt4:RelationshipType {name: "IS_PROHIBITED"})
SET rt4.source_types = ["Party", "Authority", "Role", "User", "Employee", "Action"], rt4.target_types = ["ProhibitedAction", "Action", "Activity"],
    rt4.description = "Action or party is prohibited from doing something",
    rt4.is_valid = true

MERGE (rt5:RelationshipType {name: "DEPENDS_ON"})
SET rt5.source_types = ["Condition", "Action", "Activity"], rt5.target_types = ["Precondition", "Condition", "Requirement"],
    rt5.description = "Condition depends on a precondition",
    rt5.is_valid = true

MERGE (rt6:RelationshipType {name: "APPLIES_TO"})
SET rt6.source_types = ["Obligation", "ProhibitedAction", "Rule", "Policy"], rt6.target_types = ["Party", "Authority", "Role", "User", "Employee"],
    rt6.description = "Obligation or prohibition applies to a party",
    rt6.is_valid = true
"""

CLEAR_DOCUMENT = """
MATCH (e:ExtractedEntity {document_id: $document_id})
DETACH DELETE e
"""

GET_DOCUMENT_ENTITIES = """
MATCH (e:ExtractedEntity {document_id: $document_id})
RETURN e.name AS name, e.entity_type AS type, e.mention AS mention
ORDER BY e.entity_type
"""

GET_DOCUMENT_RELATIONSHIPS = """
MATCH (e1:ExtractedEntity {document_id: $document_id})-[r]->(e2:ExtractedEntity)
RETURN e1.name AS source, e2.name AS target, type(r) AS relationship
"""

VALIDATION_CHECK = """
MATCH (rt:RelationshipType {name: $relationship})
RETURN rt.is_valid AS is_valid, rt.valid_sources AS valid_sources, 
       rt.valid_targets AS valid_targets
"""

SEED_RULES = """
// Topics
MERGE (t_approval:Topic {name: "approval"})
MERGE (t_access:Topic {name: "access"})

// Roles
MERGE (manager:Role {name: "manager"})
MERGE (intern:Role {name: "intern"})
MERGE (ceo:Role {name: "ceo"})
MERGE (analyst:Role {name: "analyst"})

// Actions
MERGE (approve_small:Action {name: "approve_request", limit: 10000})
MERGE (approve_unlimited:Action {name: "approve_request", limit: 999999999})
MERGE (view_reports:Action {name: "view_reports"})
MERGE (delete_records:Action {name: "delete_records"})

// Role → Action edges
MERGE (manager)-[:CAN_DO]->(approve_small)
MERGE (manager)-[:CAN_DO]->(view_reports)
MERGE (ceo)-[:CAN_DO]->(approve_unlimited)
MERGE (ceo)-[:CAN_DO]->(delete_records)
MERGE (analyst)-[:CAN_DO]->(view_reports)

// Rules
MERGE (r1:Rule {id: "RULE-001"})
SET r1.description = "Manager can approve requests under $10,000",
    r1.prohibited_keywords = ["intern can approve", "anyone can approve"],
    r1.severity = 1

MERGE (r2:Rule {id: "RULE-002"})
SET r2.description = "Intern cannot approve any requests under any circumstances",
    r2.prohibited_keywords = ["intern can approve", "intern is allowed to approve"],
    r2.severity = 2

MERGE (r3:Rule {id: "RULE-003"})
SET r3.description = "CEO can approve requests of any amount",
    r3.prohibited_keywords = [],
    r3.severity = 1

MERGE (r4:Rule {id: "RULE-004"})
SET r4.description = "Analysts can view reports but cannot approve or delete anything",
    r4.prohibited_keywords = ["analyst can approve", "analyst can delete"],
    r4.severity = 2

MERGE (r5:Rule {id: "RULE-005"})
SET r5.description = "No single employee can both initiate and approve the same request",
    r5.prohibited_keywords = ["can initiate and approve", "same person can approve"],
    r5.severity = 3

// Attach rules to topics
MERGE (r1)-[:APPLIES_TO]->(t_approval)
MERGE (r2)-[:APPLIES_TO]->(t_approval)
MERGE (r3)-[:APPLIES_TO]->(t_approval)
MERGE (r4)-[:APPLIES_TO]->(t_approval)
MERGE (r5)-[:APPLIES_TO]->(t_approval)
MERGE (r4)-[:APPLIES_TO]->(t_access)
"""

CHECK_ROLE_CAN_DO = """
MATCH (role:Role {name: $role})-[:CAN_DO]->(action:Action {name: $action})
RETURN count(*) > 0 AS allowed
"""

SEED_KNOWLEDGE_BASE = """
// Knowledge Base for Deterministic Compliance Queries

// PARTIES (Roles)
MERGE (manager:Party {name: "manager"})
SET manager.description = "Manager role with approval authority"

MERGE (intern:Party {name: "intern"})
SET intern.description = "Intern with no approval authority"

MERGE (ceo:Party {name: "ceo"})
SET ceo.description = "Chief Executive Officer with unlimited authority"

MERGE (analyst:Party {name: "analyst"})
SET analyst.description = "Analyst with view-only access"

MERGE (cfo:Party {name: "cfo"})
SET cfo.description = "Chief Financial Officer with financial authority"

MERGE (director:Party {name: "director"})
SET director.description = "Director with department-level authority"

// ACTIONS
MERGE (approve_request:Action {name: "approve_request"})
SET approve_request.description = "Approve a request or expense"

MERGE (delete_records:Action {name: "delete_records"})
SET delete_records.description = "Delete system records"

MERGE (view_reports:Action {name: "view_reports"})
SET view_reports.description = "View reports and data"

// AUTHORITY RELATIONSHIPS (HAS_AUTHORITY)
MERGE (manager)-[:HAS_AUTHORITY {limit: 10000}]->(approve_request)
MERGE (ceo)-[:HAS_AUTHORITY {limit: 0}]->(approve_request)
MERGE (cfo)-[:HAS_AUTHORITY {limit: 50000}]->(approve_request)
MERGE (director)-[:HAS_AUTHORITY {limit: 25000}]->(approve_request)

// PROHIBITED ACTIONS
MERGE (intern)-[:IS_PROHIBITED {justification: "Interns cannot approve any requests"}]->(prohibited_intern_approve:ProhibitedAction {name: "approve_request"})
MERGE (analyst)-[:IS_PROHIBITED {justification: "Analysts cannot approve or delete"}]->(prohibited_analyst_approve:ProhibitedAction {name: "approve_request"})
MERGE (analyst)-[:IS_PROHIBITED {justification: "Analysts cannot approve or delete"}]->(prohibited_analyst_delete:ProhibitedAction {name: "delete_records"})

// VIEW ACCESS
MERGE (manager)-[:HAS_AUTHORITY]->(view_reports)
MERGE (intern)-[:HAS_AUTHORITY]->(view_reports)
MERGE (ceo)-[:HAS_AUTHORITY]->(view_reports)
MERGE (analyst)-[:HAS_AUTHORITY]->(view_reports)
MERGE (cfo)-[:HAS_AUTHORITY]->(view_reports)
MERGE (director)-[:HAS_AUTHORITY]->(view_reports)

// DELETE ACCESS (restricted)
MERGE (ceo)-[:HAS_AUTHORITY]->(delete_records)
"""

# Conflict Detection Queries

DETECT_HIERARCHICAL_CONFLICTS = """
MATCH (p1:ExtractedEntity)-[r1:HAS_AUTHORITY]->(a:Action)
MATCH (p2:ExtractedEntity)-[r2:HAS_AUTHORITY]->(a)
WHERE p1.document_id <> p2.document_id
  AND p1.entity_type = 'Party'
  AND p2.entity_type = 'Party'
RETURN p1.name AS party1, p2.name AS party2, 
       a.name AS action,
       p1.document_id AS doc1, p2.document_id AS doc2,
       'Hierarchical Conflict: Multiple parties have authority over same action' AS conflict_type
"""

DETECT_LIMIT_CONFLICTS = """
MATCH (p:ExtractedEntity)-[r1:HAS_AUTHORITY]->(a:Action)
MATCH (p)-[r2:HAS_AUTHORITY]->(a)
WHERE r1.limit <> r2.limit
  AND r1.limit IS NOT NULL 
  AND r2.limit IS NOT NULL
RETURN p.name AS party, a.name AS action, 
       r1.limit AS limit1, r2.limit AS limit2,
       'Limit Conflict: Different limits for same party-action' AS conflict_type
"""

DETECT_PROHIBITED_AUTHORIZED_CONFLICTS = """
MATCH (p:ExtractedEntity)-[:HAS_AUTHORITY]->(a:Action)
MATCH (p)-[:IS_PROHIBITED]->(pa:ProhibitedAction)
WHERE a.name CONTAINS pa.name OR pa.name CONTAINS a.name
RETURN p.name AS party, a.name AS action, 
       pa.name AS prohibited_action,
       'Authorization Conflict: Party can and cannot perform same action' AS conflict_type
"""

DETECT_OBLIGATION_CONFLICTS = """
MATCH (p1:ExtractedEntity)-[r1:MUST_FULFILL]->(o:Obligation)
MATCH (p2:ExtractedEntity)-[r2:MUST_FULFILL]->(o)
WHERE p1.document_id <> p2.document_id
  AND p1.entity_type = 'Party'
  AND p2.entity_type = 'Party'
RETURN p1.name AS party1, p2.name AS party2,
       o.name AS obligation,
       p1.document_id AS doc1, p2.document_id AS doc2,
       'Obligation Conflict: Multiple parties have same obligation' AS conflict_type
"""

DETECT_CONFLICTS_BY_DOCUMENT = """
MATCH (e1:ExtractedEntity {document_id: $document_id})-[r1]->(e2:ExtractedEntity)
MATCH (e3:ExtractedEntity)-[r2]->(e4:ExtractedEntity)
WHERE e1.name = e3.name 
  AND e2.name = e4.name 
  AND type(r1) = type(r2)
  AND e1.document_id <> e3.document_id
RETURN e1.name AS entity1, e2.name AS entity2, 
       type(r1) AS relationship,
       e1.document_id AS source_doc, e3.document_id AS conflicting_doc,
       'Cross-document conflict detected' AS conflict_type
"""

GET_ALL_CONFLICTS = """
// Detect all types of conflicts in the database
CALL {
  // Hierarchical conflicts
  MATCH (p1:ExtractedEntity)-[r1:HAS_AUTHORITY]->(a:Action)
  MATCH (p2:ExtractedEntity)-[r2:HAS_AUTHORITY]->(a)
  WHERE p1.document_id <> p2.document_id
    AND p1.entity_type = 'Party'
    AND p2.entity_type = 'Party'
  RETURN p1.name AS entity1, p2.name AS entity2, a.name AS target,
         'hierarchical' AS conflict_type, 1 AS severity
  UNION
  // Limit conflicts
  MATCH (p:ExtractedEntity)-[r1:HAS_AUTHORITY]->(a:Action)
  MATCH (p)-[r2:HAS_AUTHORITY]->(a)
  WHERE r1.limit <> r2.limit AND r1.limit IS NOT NULL AND r2.limit IS NOT NULL
  RETURN p.name AS entity1, p.name AS entity2, a.name AS target,
         'limit' AS conflict_type, 2 AS severity
  UNION
  // Prohibited vs Authorized
  MATCH (p:ExtractedEntity)-[:HAS_AUTHORITY]->(a:Action)
  MATCH (p)-[:IS_PROHIBITED]->(pa:ProhibitedAction)
  WHERE a.name CONTAINS pa.name OR pa.name CONTAINS a.name
  RETURN p.name AS entity1, p.name AS entity2, a.name AS target,
         'prohibited' AS conflict_type, 1 AS severity
}
RETURN entity1, entity2, target, conflict_type, severity
ORDER BY severity
"""

# Rule Management Queries

SAVE_PENDING_RULE = """
MERGE (r:PendingRule {rule_id: $rule_id})
SET r.rule_type = $rule_type,
    r.source_entity = $source_entity,
    r.target_entity = $target_entity,
    r.description = $description,
    r.limit = $limit,
    r.confidence = $confidence,
    r.source_text = $source_text,
    r.source_document = $source_document,
    r.source_page = $source_page,
    r.status = 'pending',
    r.created_at = datetime()
RETURN r.rule_id AS rule_id
"""

GET_PENDING_RULES = """
MATCH (r:PendingRule)
WHERE $document_id IS NULL OR r.source_document = $document_id
RETURN r.rule_id AS rule_id,
       r.rule_type AS rule_type,
       r.source_entity AS source_entity,
       r.target_entity AS target_entity,
       r.description AS description,
       r.limit AS limit,
       r.confidence AS confidence,
       r.source_text AS source_text,
       r.source_document AS source_document,
       r.source_page AS source_page,
       r.status AS status
ORDER BY r.created_at DESC
"""

UPDATE_PENDING_RULE_STATUS = """
MATCH (r:PendingRule {rule_id: $rule_id})
SET r.status = $status
"""

UPDATE_PENDING_RULE_FIELDS = """
MATCH (r:PendingRule {rule_id: $rule_id})
SET r += $fields
RETURN r.rule_id AS rule_id
"""

APPLY_RULE_TO_GRAPH = """
MATCH (r:PendingRule {rule_id: $rule_id})
WHERE r.status = 'approved'
WITH r
CALL {
  WITH r
  MATCH (source)
  WHERE source.name = $source_name
  WITH source, r
  MATCH (target)
  WHERE target.name = $target_name
  WITH source, target, r
  CALL apoc.create.relationship(source, r.rule_type,
    CASE WHEN r.limit IS NOT NULL THEN {limit: r.limit, source_document: r.source_document, applied_at: datetime()}
         ELSE {source_document: r.source_document, applied_at: datetime()}
    END, target)
  YIELD rel
  RETURN rel
}
RETURN count(*) AS applied
"""

APPLY_RULE_TO_GRAPH_NO_APOC = """
MATCH (r:PendingRule {rule_id: $rule_id})
WHERE r.status = 'approved'
WITH r
MATCH (source)
WHERE source.name = $source_name
WITH source, r
MATCH (target)
WHERE target.name = $target_name
WITH source, target, r
CALL {
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'HAS_AUTHORITY'
  MERGE (source)-[rel:HAS_AUTHORITY {source_document: r.source_document}]->(target)
  SET rel.limit = r.limit, rel.applied_at = datetime()
  RETURN rel
  UNION
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'REQUIRES_PRECONDITION'
  MERGE (source)-[rel:REQUIRES_PRECONDITION {source_document: r.source_document}]->(target)
  SET rel.applied_at = datetime()
  RETURN rel
  UNION
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'MUST_FULFILL'
  MERGE (source)-[rel:MUST_FULFILL {source_document: r.source_document}]->(target)
  SET rel.applied_at = datetime()
  RETURN rel
  UNION
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'IS_PROHIBITED'
  MERGE (source)-[rel:IS_PROHIBITED {source_document: r.source_document}]->(target)
  SET rel.applied_at = datetime()
  RETURN rel
  UNION
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'DEPENDS_ON'
  MERGE (source)-[rel:DEPENDS_ON {source_document: r.source_document}]->(target)
  SET rel.applied_at = datetime()
  RETURN rel
  UNION
  WITH source, target, r
  WITH source, target, r
  WHERE r.rule_type = 'APPLIES_TO'
  MERGE (source)-[rel:APPLIES_TO {source_document: r.source_document}]->(target)
  SET rel.applied_at = datetime()
  RETURN rel
}
RETURN count(*) AS applied
"""

CREATE_PARTY_IF_NOT_EXISTS = """
MERGE (p:Party {name: $name})
ON CREATE SET p.description = $description, p.created_from = 'rule_management'
RETURN p.name AS name
"""

CREATE_ACTION_IF_NOT_EXISTS = """
MERGE (a:Action {name: $name})
ON CREATE SET a.description = $description, a.created_from = 'rule_management'
RETURN a.name AS name
"""

CREATE_OBLIGATION_IF_NOT_EXISTS = """
MERGE (o:Obligation {name: $name})
ON CREATE SET o.description = $description, o.created_from = 'rule_management'
RETURN o.name AS name
"""

CREATE_PROHIBITED_ACTION_IF_NOT_EXISTS = """
MERGE (pa:ProhibitedAction {name: $name})
ON CREATE SET pa.created_from = 'rule_management'
RETURN pa.name AS name
"""

CREATE_PRECONDITION_IF_NOT_EXISTS = """
MERGE (pc:Precondition {name: $name})
ON CREATE SET pc.description = $description, pc.created_from = 'rule_management'
RETURN pc.name AS name
"""

CREATE_CONDITION_IF_NOT_EXISTS = """
MERGE (c:Condition {name: $name})
ON CREATE SET c.description = $description, c.created_from = 'rule_management'
RETURN c.name AS name
"""

GET_ALL_APPLIED_RULES = """
MATCH (source)-[r]->(target)
WHERE r.source_document IS NOT NULL
RETURN source.name AS source,
       type(r) AS rule_type,
       target.name AS target,
       r.limit AS limit,
       r.source_document AS source_document,
       r.applied_at AS applied_at
ORDER BY r.applied_at DESC
"""

DELETE_PENDING_RULE = """
MATCH (r:PendingRule {rule_id: $rule_id})
DELETE r
"""

GET_PENDING_RULES_STATS = """
MATCH (r:PendingRule)
RETURN count(r) AS total,
       count(CASE WHEN r.status = 'pending' THEN r END) AS pending,
       count(CASE WHEN r.status = 'approved' THEN r END) AS approved,
       count(CASE WHEN r.status = 'rejected' THEN r END) AS rejected,
       collect(DISTINCT r.source_document) AS documents
"""
