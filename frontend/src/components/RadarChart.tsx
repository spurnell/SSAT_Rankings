"use client";

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import { CategoryInfo } from "@/lib/api";

interface Player2Scores {
  scores: Record<string, number>;
  name?: string;
}

interface RadarChartProps {
  // Dynamic category scores
  categoryScores: Record<string, number>;
  categories: CategoryInfo[];
  playerName?: string;
  player2?: Player2Scores;
}

// Short display names for categories
const SHORT_NAMES: Record<string, string> = {
  run_defense: "Run Def",
  pass_rush: "Pass Rush",
  coverage: "Coverage",
  playmaking: "Playmaking",
  efficiency: "Efficiency",
  volume: "Volume",
  ball_security: "Ball Sec",
  scoring: "Scoring",
  receiving: "Receiving",
  accuracy: "Accuracy",
  clutch: "Clutch",
};

function getShortName(category: CategoryInfo): string {
  return SHORT_NAMES[category.id] || category.name;
}

export default function RadarChart({
  categoryScores,
  categories,
  playerName,
  player2,
}: RadarChartProps) {
  const data = categories.map((cat) => ({
    category: getShortName(cat),
    score: categoryScores[cat.id] || 80,
    score2: player2?.scores[cat.id],
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: "#64748b", fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={45}
          domain={[40, 100]}
          tick={{ fill: "#94a3b8", fontSize: 10 }}
          tickCount={5}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: "6px",
          }}
          formatter={(value) => [typeof value === "number" ? value.toFixed(1) : value, "Score"]}
        />
        <Radar
          name={playerName || "Player 1"}
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.4}
          strokeWidth={2}
        />
        {player2 && (
          <Radar
            name={player2.name || "Player 2"}
            dataKey="score2"
            stroke="#f97316"
            fill="#f97316"
            fillOpacity={0.4}
            strokeWidth={2}
          />
        )}
        {player2 && (
          <Legend
            content={() => (
              <div className="flex justify-center gap-6 text-sm mt-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                  <span className="text-slate-600">{playerName || "Player 1"}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-orange-500"></span>
                  <span className="text-slate-600">{player2.name || "Player 2"}</span>
                </div>
              </div>
            )}
          />
        )}
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}

// Legacy props interface for backward compatibility
interface LegacyRadarChartProps {
  runDefense: number;
  passRush: number;
  coverage: number;
  playmaking: number;
  playerName?: string;
  player2?: {
    runDefense: number;
    passRush: number;
    coverage: number;
    playmaking: number;
    name?: string;
  };
}

// Legacy wrapper component
export function LegacyRadarChart({
  runDefense,
  passRush,
  coverage,
  playmaking,
  playerName,
  player2,
}: LegacyRadarChartProps) {
  const categories: CategoryInfo[] = [
    { id: "run_defense", name: "Run Defense" },
    { id: "pass_rush", name: "Pass Rush" },
    { id: "coverage", name: "Coverage" },
    { id: "playmaking", name: "Playmaking" },
  ];

  const categoryScores: Record<string, number> = {
    run_defense: runDefense,
    pass_rush: passRush,
    coverage: coverage,
    playmaking: playmaking,
  };

  const player2Data = player2
    ? {
        scores: {
          run_defense: player2.runDefense,
          pass_rush: player2.passRush,
          coverage: player2.coverage,
          playmaking: player2.playmaking,
        },
        name: player2.name,
      }
    : undefined;

  return (
    <RadarChart
      categoryScores={categoryScores}
      categories={categories}
      playerName={playerName}
      player2={player2Data}
    />
  );
}
