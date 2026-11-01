import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { apiClient } from "../services/apiClient";
import { getErrorMessage } from "../utils/errors";

type NodeStatus = {
  hospital: string;
  port: number;
  tcp_listening: boolean;
  local_training_evidence: boolean;
  participated_in_fedavg_abc: boolean;
  own_local_training?: {
    epochs: number | null;
    training_loss: number | null;
    training_seconds: number | null;
    patch_size: number[] | null;
    federated_round_completed: boolean;
    purpose: string | null;
  } | null;
};

type Experiment = {
  id: string;
  title: string;
  metadata_available: boolean;
  round: number | null;
  participants: string[];
  total_samples: number | null;
  aggregation: string | null;
  changed_global_parameters: number | null;
  global_update_l2_norm: number | null;
  secure_aggregation: boolean;
  distributed_privacy_verified: boolean;
  zk_proof_generated: boolean;
  blockchain_committed: boolean;
  clinical_validation: boolean;
  single_process_smoke_test: boolean;
  secure_sum_mismatches: number | null;
  checkpoint: {
    sha256: string | null;
    integrity: string;
    size_bytes: number | null;
  };
};

type FederationSummary = {
  generated_at: string;
  evidence_source: string;
  flower: {
    superlink_tcp_listening: boolean;
    fleet_api_tcp_listening: boolean;
    nodes: NodeStatus[];
  };
  experiments: Experiment[];
  protocol_test: {
    round_label: number | null;
    purpose: string | null;
    full_model_proven: boolean;
    live_proof_submitted: boolean;
    blockchain_verification_completed: boolean;
  };
  disclaimer: string;
};

function YesNo({ value }: { value: boolean }) {
  return (
    <span className={value ? "text-emerald-300" : "text-amber-300"}>
      {value ? "Yes" : "No"}
    </span>
  );
}

function ModelCard({ item }: { item: Experiment }) {
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">
            {item.title}
          </h3>
          <p className="mt-1 text-sm text-muted">
            {item.single_process_smoke_test
              ? "Single-process research smoke test"
              : "Historical aggregation prototype"}
          </p>
        </div>
        <span className="rounded-lg border border-border px-3 py-1 text-xs text-muted">
          {item.metadata_available ? "Evidence available" : "Unavailable"}
        </span>
      </div>

      <dl className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-muted">Round</dt>
          <dd className="font-medium text-ink">
            {item.round ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Participants</dt>
          <dd className="font-medium text-ink">
            {item.participants.length
              ? item.participants.join(" + ")
              : "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Training samples</dt>
          <dd className="font-medium text-ink">
            {item.total_samples ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Aggregation method</dt>
          <dd className="break-words text-sm text-ink">
            {item.aggregation ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Changed parameters</dt>
          <dd className="font-medium text-ink">
            {item.changed_global_parameters?.toLocaleString()
              ?? "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Update L2 norm</dt>
          <dd className="font-medium text-ink">
            {item.global_update_l2_norm?.toFixed(6)
              ?? "Not recorded"}
          </dd>
        </div>
      </dl>

      <div className="mt-5 rounded-lg border border-border bg-slate-900/50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">
          Global checkpoint SHA256
        </p>
        <p className="mt-2 break-all font-mono text-xs text-cyan-200">
          {item.checkpoint.sha256 ?? "Checkpoint unavailable"}
        </p>
        <p className="mt-2 text-xs text-muted">
          Integrity: {item.checkpoint.integrity.replaceAll("_", " ")}
        </p>
      </div>

      <div className="mt-5 grid gap-2 text-sm text-muted sm:grid-cols-2">
        <p>ZK proof: <YesNo value={item.zk_proof_generated} /></p>
        <p>On-chain: <YesNo value={item.blockchain_committed} /></p>
        <p>
          Distributed privacy verified:{" "}
          <YesNo value={item.distributed_privacy_verified} />
        </p>
        <p>
          Clinical validation:{" "}
          <YesNo value={item.clinical_validation} />
        </p>
      </div>
    </Card>
  );
}

export function FederationDashboardPage() {
  const [data, setData] = useState<FederationSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setLoading(true);
    setError(null);

    apiClient
      .request<FederationSummary>("/federation/summary", {
        signal: controller.signal,
      })
      .then((response) => {
        if (active) setData(response);
      })
      .catch((reason: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(getErrorMessage(reason));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [refreshKey]);

  return (
    <div className="grid gap-6">
      <PageHeader
        title="Federated Global Model"
        description="Read-only Flower network status and historical 3D U-Net federation evidence."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Historical experiments are separate from live node connectivity.
        </p>
        <button
          type="button"
          onClick={() => setRefreshKey((value) => value + 1)}
          className="rounded-lg border border-violet-400/40 bg-violet-500/20 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500/30"
        >
          Refresh evidence
        </button>
      </div>

      {loading ? (
        <Card><p className="text-muted">Loading federation evidence…</p></Card>
      ) : null}

      {error ? (
        <Card>
          <p className="text-rose-300" role="alert">
            Federation API error: {error}
          </p>
        </Card>
      ) : null}

      {data ? (
        <>
          <Card>
            <h2 className="text-lg font-semibold text-ink">
              Flower runtime connectivity
            </h2>
            <p className="mt-2 text-sm text-muted">
              These are TCP listening checks, not proof of active
              training or completed federated rounds.
            </p>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-slate-900/60 p-4">
                <p className="font-semibold text-ink">
                  SuperLink :18080
                </p>
                <p className="text-sm text-muted">
                  Listening:{" "}
                  <YesNo value={data.flower.superlink_tcp_listening} />
                </p>
              </div>
              <div className="rounded-lg bg-slate-900/60 p-4">
                <p className="font-semibold text-ink">
                  Fleet API :18082
                </p>
                <p className="text-sm text-muted">
                  Listening:{" "}
                  <YesNo value={data.flower.fleet_api_tcp_listening} />
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {data.flower.nodes.map((node) => (
                <div
                  key={node.hospital}
                  className="rounded-lg border border-border bg-slate-900/40 p-4"
                >
                  <h3 className="font-semibold text-ink">
                    Hospital {node.hospital}
                  </h3>
                  <p className="mt-2 text-xs text-muted">
                    SuperNode port {node.port}
                  </p>
                  <p className="mt-2 text-sm text-muted">
                    Listening: <YesNo value={node.tcp_listening} />
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    Local evidence:{" "}
                    <YesNo value={node.local_training_evidence} />
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    FedAvg A+B+C participant:{" "}
                    <YesNo value={node.participated_in_fedavg_abc} />
                  </p>

                  {node.own_local_training ? (
                    <div className="mt-3 border-t border-border pt-3 text-xs text-muted">
                      <p>Your local smoke-test epochs:{" "}
                        {node.own_local_training.epochs ?? "N/A"}
                      </p>
                      <p>Training loss:{" "}
                        {node.own_local_training.training_loss?.toFixed(4)
                          ?? "N/A"}
                      </p>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>

          <h2 className="text-xl font-semibold text-ink">
            Historical global model artifacts
          </h2>

          <div className="grid gap-5 xl:grid-cols-2">
            {data.experiments.map((experiment) => (
              <ModelCard item={experiment} key={experiment.id} />
            ))}
          </div>

          <Card>
            <h2 className="text-lg font-semibold text-ink">
              ZKP protocol evidence — Round{" "}
              {data.protocol_test.round_label ?? "unknown"}
            </h2>
            <p className="mt-2 text-sm text-muted">
              {data.protocol_test.purpose ?? "No protocol evidence available."}
            </p>
            <div className="mt-4 grid gap-3 text-sm text-muted sm:grid-cols-3">
              <p>Full model proven:{" "}
                <YesNo value={data.protocol_test.full_model_proven} />
              </p>
              <p>Live proof submitted:{" "}
                <YesNo value={data.protocol_test.live_proof_submitted} />
              </p>
              <p>Blockchain verified:{" "}
                <YesNo value={
                  data.protocol_test.blockchain_verification_completed
                } />
              </p>
            </div>
          </Card>

          <Card>
            <p className="text-sm text-amber-200">
              {data.disclaimer}
            </p>
            <p className="mt-2 text-xs text-muted">
              Snapshot: {new Date(data.generated_at).toLocaleString()}
            </p>
          </Card>
        </>
      ) : null}
    </div>
  );
}
