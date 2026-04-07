import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const nodeColors = {
  Party: '#8b5cf6',
  Authority: '#3b82f6',
  Action: '#10b981',
  Obligation: '#f59e0b',
  ProhibitedAction: '#ef4444',
  Condition: '#a855f7',
  Precondition: '#06b6d4',
  Role: '#ec4899',
  User: '#14b8a6',
  Employee: '#f97316',
};

const entityTypeColors = Object.entries(nodeColors).reduce((acc, [key, value]) => {
  acc[key.toLowerCase()] = value;
  return acc;
}, {});

const getNodeColor = (entityType) => {
  const key = entityType?.toLowerCase() || 'party';
  return entityTypeColors[key] || '#8b5cf6';
};

const nodeVariants = {
  hidden: { scale: 0, opacity: 0 },
  visible: { 
    scale: 1, 
    opacity: 1,
    transition: { type: 'spring', stiffness: 400, damping: 15 }
  }
};

const connectionVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: { 
    pathLength: 1, 
    opacity: 1,
    transition: { duration: 0.8, ease: 'easeInOut' }
  }
};

function OntologyCanvas({ entities = [], relationships = [], loading = false }) {
  const [positions, setPositions] = useState({});
  const [showCanvas, setShowCanvas] = useState(false);

  useEffect(() => {
    if (entities.length > 0 || loading) {
      setShowCanvas(true);
    }
  }, [entities, loading]);

  useEffect(() => {
    const newPositions = {};
    const centerX = 450;
    const centerY = 300;
    const radius = Math.min(Math.max(entities.length * 50, 150), 280);
    
    entities.forEach((entity, index) => {
      const angle = (index / entities.length) * 2 * Math.PI - Math.PI / 2;
      newPositions[entity.name] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });
    
    setPositions(newPositions);
  }, [entities]);

  const skeletonNodes = [1, 2, 3, 4, 5];

  if (!showCanvas && entities.length === 0 && !loading) {
    return (
      <div className="ontology-canvas-empty">
        <div className="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="3"/>
            <circle cx="4" cy="8" r="2"/>
            <circle cx="20" cy="8" r="2"/>
            <circle cx="4" cy="16" r="2"/>
            <circle cx="20" cy="16" r="2"/>
            <path d="M6.5 9.5L10 11M18 11L17.5 9.5"/>
            <path d="M6.5 14.5L10 13M18 13L17.5 14.5"/>
          </svg>
        </div>
        <p>Extracted entities will appear here as an interactive graph</p>
      </div>
    );
  }

  if (loading && entities.length === 0) {
    return (
      <div className="ontology-canvas">
        <svg viewBox="0 0 900 600" className="canvas-svg">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          {skeletonNodes.map((_, i) => {
            const angle = (i / skeletonNodes.length) * 2 * Math.PI - Math.PI / 2;
            const x = 450 + 200 * Math.cos(angle);
            const y = 300 + 200 * Math.sin(angle);
            return (
              <g key={i}>
                <motion.circle
                  cx={x}
                  cy={y}
                  r="28"
                  fill="transparent"
                  stroke="var(--border-medium)"
                  strokeWidth="2"
                  initial={{ opacity: 0.3 }}
                  animate={{ 
                    opacity: [0.3, 0.6, 0.3],
                    scale: [1, 1.05, 1]
                  }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity, 
                    delay: i * 0.2 
                  }}
                />
                <motion.circle
                  cx={x}
                  cy={y}
                  r="20"
                  fill="var(--bg-elevated)"
                  stroke="var(--border-medium)"
                  strokeWidth="1"
                  initial={{ opacity: 0.3 }}
                  animate={{ opacity: [0.3, 0.5, 0.3] }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity, 
                    delay: i * 0.2 
                  }}
                />
              </g>
            );
          })}
        </svg>
      </div>
    );
  }

  return (
    <div className="ontology-canvas">
      <svg viewBox="0 0 900 600" className="canvas-svg">
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="red-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="node-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000" floodOpacity="0.4"/>
          </filter>
          <linearGradient id="laser-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#22d3ee" stopOpacity="1" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.6" />
          </linearGradient>
          <linearGradient id="prohibited-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#f87171" stopOpacity="1" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.6" />
          </linearGradient>
        </defs>

        <rect width="900" height="600" fill="transparent" />

        <AnimatePresence>
          {relationships.map((rel, index) => {
            const sourcePos = positions[rel.source];
            const targetPos = positions[rel.target];
            
            if (!sourcePos || !targetPos) return null;
            
            const isProhibited = rel.relationship === 'IS_PROHIBITED' || rel.relationship?.toLowerCase().includes('prohibited');
            const midX = (sourcePos.x + targetPos.x) / 2;
            const midY = (sourcePos.y + targetPos.y) / 2;
            const controlOffset = 25;
            const controlX = midX + (sourcePos.y - targetPos.y) / 4;
            const controlY = midY + (targetPos.x - sourcePos.x) / 4;
            
            const pathData = `M ${sourcePos.x} ${sourcePos.y} Q ${controlX} ${controlY} ${targetPos.x} ${targetPos.y}`;
            
            return (
              <motion.g key={`rel-${index}`}
                initial="hidden"
                animate="visible"
                variants={connectionVariants}
              >
                <path
                  d={pathData}
                  fill="none"
                  stroke={isProhibited ? 'url(#prohibited-gradient)' : 'url(#laser-gradient)'}
                  strokeWidth={isProhibited ? 3 : 2}
                  strokeLinecap="round"
                  filter={isProhibited ? 'url(#red-glow)' : 'url(#glow)'}
                  className={isProhibited ? 'animate-shake' : ''}
                />
                <rect
                  x={midX - 50}
                  y={midY - 12}
                  width="100"
                  height="24"
                  rx="12"
                  fill="rgba(15, 15, 35, 0.9)"
                  stroke={isProhibited ? '#ef4444' : '#06b6d4'}
                  strokeWidth="1"
                />
                <text
                  x={midX}
                  y={midY + 4}
                  textAnchor="middle"
                  fill={isProhibited ? '#fca5a5' : '#22d3ee'}
                  fontSize="10"
                  fontWeight="600"
                >
                  {rel.relationship}
                </text>
              </motion.g>
            );
          })}
        </AnimatePresence>

        <AnimatePresence>
          {entities.map((entity, index) => {
            const pos = positions[entity.name];
            if (!pos) return null;
            
            const color = getNodeColor(entity.entity_type);
            
            return (
              <motion.g
                key={entity.name}
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={nodeVariants}
                style={{ transitionDelay: `${index * 0.08}s` }}
              >
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="32"
                  fill={color}
                  fillOpacity="0.15"
                  stroke={color}
                  strokeWidth="2"
                  filter="url(#node-shadow)"
                />
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="26"
                  fill="rgba(15, 15, 35, 0.95)"
                  stroke={color}
                  strokeWidth="2"
                />
                <text
                  x={pos.x}
                  y={pos.y - 4}
                  textAnchor="middle"
                  fill="#f9fafb"
                  fontSize="11"
                  fontWeight="600"
                >
                  {entity.name.length > 12 ? entity.name.slice(0, 12) + '..' : entity.name}
                </text>
                <text
                  x={pos.x}
                  y={pos.y + 10}
                  textAnchor="middle"
                  fill={color}
                  fontSize="9"
                  fontWeight="500"
                >
                  {entity.entity_type}
                </text>
              </motion.g>
            );
          })}
        </AnimatePresence>
      </svg>

      <style>{`
        .ontology-canvas {
          background: linear-gradient(135deg, rgba(22, 33, 62, 0.8), rgba(15, 15, 35, 0.9));
          border-radius: 16px;
          padding: 20px;
          margin-top: 20px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }
        
        .canvas-svg {
          width: 100%;
          height: auto;
          min-height: 400px;
        }
        
        .ontology-canvas-empty {
          background: linear-gradient(135deg, rgba(22, 33, 62, 0.5), rgba(15, 15, 35, 0.6));
          border-radius: 16px;
          padding: 60px 40px;
          margin-top: 20px;
          border: 1px dashed rgba(255, 255, 255, 0.15);
          text-align: center;
        }
        
        .empty-icon {
          color: rgba(139, 92, 246, 0.4);
          margin-bottom: 16px;
        }
        
        .ontology-canvas-empty p {
          color: rgba(156, 163, 175, 0.7);
          font-size: 0.9rem;
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0) translateY(0); }
          25% { transform: translateX(-2px) translateY(-1px); }
          75% { transform: translateX(2px) translateY(1px); }
        }
        
        .animate-shake {
          animation: shake 0.4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default OntologyCanvas;
