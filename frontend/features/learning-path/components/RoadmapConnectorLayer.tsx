import { connectorPath, type RoadmapConnectorModel, type RoadmapNodeModel } from "../roadmap-model";

interface RoadmapConnectorLayerProps {
  connectors: RoadmapConnectorModel[];
  nodesById: Map<string, RoadmapNodeModel>;
}

export default function RoadmapConnectorLayer({ connectors, nodesById }: RoadmapConnectorLayerProps) {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
      {connectors.map((connector) => {
        const from = nodesById.get(connector.fromId);
        const to = nodesById.get(connector.toId);
        if (!from || !to) return null;

        return (
          <path
            key={connector.id}
            d={connectorPath(from, to)}
            fill="none"
            stroke={connector.isRecommended ? "#f59e0b" : "#2563eb"}
            strokeWidth={connector.isRecommended ? 4 : 3}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={connector.isRecommended ? "0" : "1 8"}
            opacity={connector.isRecommended ? 0.95 : 0.55}
          />
        );
      })}
    </svg>
  );
}
