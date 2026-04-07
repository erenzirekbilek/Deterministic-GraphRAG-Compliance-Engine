import logging
import re
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_QUERIES = {
    "authority": """
    MATCH (p:Party {name: $party})-[r:HAS_AUTHORITY]->(a:Action {name: $action})
    RETURN r.limit AS limit, r.conditions AS conditions
    """,
    
    "prohibited": """
    MATCH (p:Party {name: $party})-[r:IS_PROHIBITED]->(pa:ProhibitedAction)
    WHERE pa.name CONTAINS $action OR $action CONTAINS pa.name
    RETURN pa.name AS prohibited_action, r.justification AS reason
    """,
    
    "obligation": """
    MATCH (p:Party {name: $party})-[r:MUST_FULFILL]->(o:Obligation)
    RETURN o.name AS obligation, r.due_date AS due_date
    """,
    
    "precondition": """
    MATCH (a:Action {name: $action})-[r:REQUIRES_PRECONDITION]->(p:Precondition)
    RETURN p.name AS precondition, p.description AS description
    """,
    
    "can_approve": """
    MATCH (p:Party {name: $party})-[:HAS_AUTHORITY]->(a:Action {name: 'approve_request'})
    RETURN a.limit AS approval_limit
    """,
    
    "role_permissions": """
    MATCH (role:Party {name: $role})-[rel]->(action:Action)
    RETURN action.name AS action, type(rel) AS relationship, action.limit AS limit
    """
}


class DeterministicQueryService:
    def __init__(self, graph: Neo4jClient):
        self.graph = graph
        self.knowledge_base = KNOWLEDGE_BASE_QUERIES

    def extract_party_from_question(self, question: str) -> str:
        """Extract the party/role from the question."""
        question_lower = question.lower()
        
        roles = ["manager", "ceo", "intern", "analyst", "director", "employee", "cfo", "cto", "vp", "president"]
        
        for role in roles:
            if role in question_lower:
                return role
        
        return None

    def extract_action_from_question(self, question: str) -> str:
        """Extract the action from the question."""
        question_lower = question.lower()
        
        actions = {
            "approve": "approve_request",
            "approve request": "approve_request",
            "delete": "delete_records",
            "delete records": "delete_records",
            "view reports": "view_reports",
            "view": "view_reports",
            "sign": "sign_document",
            "delegate": "delegate_authority"
        }
        
        for key, action in actions.items():
            if key in question_lower:
                return action
        
        return None

    def extract_amount_from_question(self, question: str) -> float:
        """Extract monetary amount from question."""
        import re
        patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*)\s*dollars?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, question)
            if matches:
                amount_str = matches[0].replace(',', '')
                return float(amount_str)
        
        return None

    def check_authority(self, party: str, action: str, amount: float = None) -> dict:
        """Deterministically check if party has authority for action."""
        result = self.graph.run_raw(
            self.knowledge_base["authority"],
            {"party": party, "action": action}
        )
        
        if not result:
            return {
                "deterministic_result": False,
                "reason": f"No authority record found for '{party}' to perform '{action}'",
                "query_used": "authority"
            }
        
        limit = result[0].get("limit")
        
        if limit is None:
            return {
                "deterministic_result": True,
                "reason": f"'{party}' has unlimited authority to '{action}'",
                "query_used": "authority",
                "limit": None
            }
        
        if amount is not None and limit is not None:
            if amount <= limit:
                return {
                    "deterministic_result": True,
                    "reason": f"'{party}' can '{action}' (amount ${amount} is within ${limit} limit)",
                    "query_used": "authority",
                    "limit": limit
                }
            else:
                return {
                    "deterministic_result": False,
                    "reason": f"'{party}' cannot '{action}' (amount ${amount} exceeds ${limit} limit)",
                    "query_used": "authority",
                    "limit": limit
                }
        
        return {
            "deterministic_result": True,
            "reason": f"'{party}' has authority to '{action}'",
            "query_used": "authority",
            "limit": limit
        }

    def check_prohibited(self, party: str, action: str) -> dict:
        """Deterministically check if action is prohibited for party."""
        result = self.graph.run_raw(
            self.knowledge_base["prohibited"],
            {"party": party, "action": action}
        )
        
        if result:
            return {
                "deterministic_result": False,
                "reason": f"Prohibited: {result[0].get('prohibited_action')}",
                "query_used": "prohibited",
                "details": result[0]
            }
        
        return {
            "deterministic_result": True,
            "reason": f"No prohibition found for '{party}' to '{action}'",
            "query_used": "prohibited"
        }

    def answer_question(self, question: str) -> dict:
        """
        Answer a compliance question deterministically by querying Neo4j FIRST.
        Returns a mathematically definite Yes/No result.
        """
        party = self.extract_party_from_question(question)
        action = self.extract_action_from_question(question)
        amount = self.extract_amount_from_question(question)
        
        if not party:
            return {
                "deterministic_result": None,
                "reason": "Could not identify party/role in question. Please specify (e.g., manager, CEO, intern)",
                "requires_more_info": True
            }
        
        if not action:
            return {
                "deterministic_result": None,
                "reason": "Could not identify action in question. Please specify (e.g., approve, delete, view)",
                "requires_more_info": True
            }
        
        prohibited_check = self.check_prohibited(party, action)
        if not prohibited_check["deterministic_result"]:
            return prohibited_check
        
        authority_check = self.check_authority(party, action, amount)
        
        return authority_check

    def get_knowledge_base_summary(self) -> dict:
        """Get summary of all knowledge base rules."""
        roles_query = "MATCH (p:Party) RETURN p.name AS party, labels(p) AS labels"
        roles = self.graph.run_raw(roles_query)
        
        actions_query = "MATCH (a:Action) RETURN a.name AS action, a.limit AS limit"
        actions = self.graph.run_raw(actions_query)
        
        return {
            "parties": [r["party"] for r in roles if r.get("party")],
            "actions": [{"name": a["action"], "limit": a.get("limit")} for a in actions if a.get("action")]
        }
