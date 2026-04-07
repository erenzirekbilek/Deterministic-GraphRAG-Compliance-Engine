GET_RULES_BY_TOPIC = """
MATCH (r:Rule)-[:APPLIES_TO]->(t:Topic {name: $topic})
RETURN r.id AS id, r.description AS description,
       r.prohibited_keywords AS prohibited_keywords, r.severity AS severity
ORDER BY r.severity DESC
"""

GET_ALL_RULES = """
MATCH (r:Rule)
RETURN r.id AS id, r.description AS description,
       r.prohibited_keywords AS prohibited_keywords, r.severity AS severity
"""

GET_ROLE_PERMISSIONS = """
MATCH (role:Role {name: $role})-[rel]->(action:Action)
RETURN type(rel) AS permission_type, action.name AS action, action.limit AS limit
"""

CHECK_ROLE_CAN_DO = """
MATCH (role:Role {name: $role})-[:CAN_DO]->(action:Action {name: $action})
RETURN count(*) > 0 AS allowed
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
