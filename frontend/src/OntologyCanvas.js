import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const nodeColors = {
  Party: '#7c3aed',
  Authority: '#3b82f6',
  Action: '#10b981',
  Obligation: '#f59e0b',
  ProhibitedAction: '#ef4444',
  Condition: '#8b5cf6',
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
  return entityTypeColors[key] || '#7c3aed';
};

const variants = {
  initial: { scale: 0, opacity: 0 },
  animate: { 
    scale: 1, 
    opacity: 1,
    transition: { type: 'spring', stiffness: 300, damping: 20 }
  },
  exit: { scale: 0, opacity: 0 }
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

function OntologyCanvas({ entities = [], relationships = [] }) {
  const [positions, setPositions] = useState({});
  const [showCanvas, setShowCanvas] = useState(false);

  useEffect(() => {
    if (entities.length > 0) {
      setShowCanvas(true);
    }
  }, [entities]);

  useEffect(() => {
    const newPositions = {};
    const centerX = 400;
    const centerY = 300;
    const radius = Math.min(entities.length * 40, 250);
    
    entities.forEach((entity, index) => {
      const angle = (index / entities.length) * 2 * Math.PI - Math.PI / 2;
      newPositions[entity.name] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });
    
    setPositions(newPositions);
  }, [entities]);

  if (!showCanvas && entities.length === 0) {
    return (
      <div className="ontology-canvas-empty">
        <p className="text-gray-500 text-center py-8">
          Extracted entities will appear here as interactive nodes
        </p>
      </div>
    );
  }

  return (
    <div className="ontology-canvas">
      <svg viewBox="0 0 800 600" className="canvas-svg">
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="red-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <linearGradient id="laser-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#00d4ff" stopOpacity="1" />
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="prohibited-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#ef4444" stopOpacity="1" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.8" />
          </linearGradient>
        </defs>

        <AnimatePresence>
          {relationships.map((rel, index) => {
            const sourcePos = positions[rel.source];
            const targetPos = positions[rel.target];
            
            if (!sourcePos || !targetPos) return null;
            
            const isProhibited = rel.relationship === 'IS_PROHIBITED' || rel.relationship === 'prohibited';
            const midX = (sourcePos.x + targetPos.x) / 2;
            const midY = (sourcePos.y + targetPos.y) / 2;
            const controlX = midX + (Math.random() - 0.5) * 30;
            const controlY = midY + (Math.random() - 0.5) * 30;
            
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
                  strokeWidth={isProhibited ? 4 : 2}
                  strokeLinecap="round"
                  filter={isProhibited ? 'url(#red-glow)' : 'url(#glow)'}
                  className={isProhibited ? 'animate-shake' : ''}
                  style={{
                    animation: isProhibited ? 'shake 0.5s ease-in-out infinite' : 'none'
                  }}
                />
                <text
                  x={midX}
                  y={midY - 10}
                  textAnchor="middle"
                  fill={isProhibited ? '#ef4444' : '#00d4ff'}
                  fontSize="12"
                  fontWeight="bold"
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
                style={{ transitionDelay: `${index * 0.1}s` }}
              >
                <motion.circle
                  cx={pos.x}
                  cy={pos.y}
                  r="35"
                  fill={color}
                  filter="url(#glow)"
                  whileHover={{ scale: 1.2 }}
                  whileTap={{ scale: 0.9 }}
                  className="cursor-pointer"
                />
                <text
                  x={pos.x}
                  y={pos.y}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize="11"
                  fontWeight="600"
                  dy="4"
                >
                  {entity.name.length > 10 ? entity.name.slice(0, 10) + '...' : entity.name}
                </text>
                <text
                  x={pos.x}
                  y={pos.y + 20}
                  textAnchor="middle"
                  fill="#aaa"
                  fontSize="9"
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
          background: rgba(0, 0, 0, 0.3);
          border-radius: 12px;
          padding: 20px;
          margin-top: 20px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .canvas-svg {
          width: 100%;
          height: auto;
          min-height: 400px;
        }
        
        .ontology-canvas-empty {
          background: rgba(0, 0, 0, 0.2);
          border-radius: 12px;
          padding: 40px;
          margin-top: 20px;
          border: 1px dashed rgba(255, 255, 255, 0.2);
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-2px); }
          75% { transform: translateX(2px); }
        }
        
        .animate-shake {
          animation: shake 0.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default OntologyCanvas;
