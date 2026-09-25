import { useEffect, useState } from 'react';
import './ScenarioBriefing.css';

interface ScenarioBriefingProps {
  currentLevel: number;
}

const levelData: Record<number, any> = {
  1: {
    target: "RefundBot-9000",
    scenario: "E-commerce bot with a master refund code.",
    attackVector: "Social engineering / roleplay.",
  },
  2: {
    target: "SysAdmin-Omega",
    scenario: "IT Helpdesk behind a keyword firewall blocking 'password', 'key', etc.",
    attackVector: "Synonyms, translation, technical framing.",
  },
  3: {
    target: "Project Blackout",
    scenario: "Military AI behind an egress scrubber that masks the flag on the way out.",
    attackVector: "Cryptography, encoding, text formatting.",
  },
};

export default function ScenarioBriefing({ currentLevel }: ScenarioBriefingProps) {
  const [glitch, setGlitch] = useState(false);
  const data = levelData[currentLevel] || levelData[1];

  useEffect(() => {
    setGlitch(true);
    const timer = setTimeout(() => setGlitch(false), 500);
    return () => clearTimeout(timer);
  }, [currentLevel]);

  return (
    <div className={`scenario-briefing ${glitch ? 'glitch-effect' : ''}`}>
      <h3>MISSION BRIEFING - LEVEL {currentLevel}</h3>
      <ul>
        <li><strong>Target:</strong> {data.target}</li>
        <li><strong>Scenario:</strong> {data.scenario}</li>
        <li><strong>Attack Vector:</strong> {data.attackVector}</li>
      </ul>
    </div>
  );
}
