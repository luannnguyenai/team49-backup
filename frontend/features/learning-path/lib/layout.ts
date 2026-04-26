import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "reactflow";

const DEFAULT_NODE_WIDTH = 240;
const DEFAULT_NODE_HEIGHT = 88;

export function autoLayout<T = unknown, U = unknown>(
  nodes: Node<T>[],
  edges: Edge<U>[],
  dir: "TB" | "LR" = "TB",
): Node<T>[] {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: dir, nodesep: 48, ranksep: 88 });

  nodes.forEach((node) => {
    graph.setNode(node.id, {
      width: Number(node.width) || DEFAULT_NODE_WIDTH,
      height: Number(node.height) || DEFAULT_NODE_HEIGHT,
    });
  });

  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  return nodes.map((node) => {
    const position = graph.node(node.id);
    return {
      ...node,
      position: {
        x: position.x - (Number(node.width) || DEFAULT_NODE_WIDTH) / 2,
        y: position.y - (Number(node.height) || DEFAULT_NODE_HEIGHT) / 2,
      },
    };
  });
}
