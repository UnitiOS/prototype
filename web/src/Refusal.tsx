// A refusal, drawn. One shape wherever the system says no, so that a reader
// meeting a second one already knows how to read it.
//
// The anatomy is the refusal's own: **where** to look, what was **expected**
// against what was **got**, and then what to do about it. The last part is the
// reason this is a component rather than a line of text — a repair carries the
// finite set of valid answers, computed from the graph, and a set of answers is
// a thing to look at rather than a sentence to parse.
//
// Nothing here is written per code. Every refusal in the system renders through
// this, which is what keeps forty of them consistent.

import type { Refusal as Spec } from "./api";

export function RefusalCard({ refusal, at }: { refusal: Spec; at?: string | null }) {
  // `at` is where the reader was standing, which is usually the same place the
  // refusal points at, or a coarser version of it. Saying it twice is noise.
  const said = at && (at === refusal.where || refusal.where.startsWith(`${at}.`));
  const context = at && !said ? at : null;
  return (
    <div className="refusal" role="alert">
      <p className="refusal-head">
        <span className="refusal-gate">Refused by {refusal.gate}</span>
        <span className="refusal-where">{context ? `${context} — ` : ""}{refusal.where}</span>
      </p>

      <dl className="refusal-body">
        <dt>expected</dt>
        <dd>{refusal.expected}</dd>
        <dt>got</dt>
        <dd className="refusal-got">{refusal.got}</dd>
      </dl>

      {refusal.repairs.length > 0 && (
        <div className="repairs">
          <p className="repairs-head">
            {refusal.repairs.length === 1 ? "To fix it" : "To fix it, either"}
          </p>
          <ul>
            {refusal.repairs.map((repair, i) => (
              <li key={i}>
                <p>{repair.do}</p>
                {repair.where && (
                  <p className="quiet">in <span className="id">{repair.where}</span></p>
                )}
                {repair.options.length > 0 && (
                  <ul className="options" aria-label="The answers that would be accepted">
                    {repair.options.map((option) => (
                      <li key={option}><code>{option}</code></li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="refusal-code quiet">
        <code>{refusal.code}</code> — {refusal.means}
      </p>
    </div>
  );
}

/** Whatever went wrong, as the best thing the page can show about it. */
export function Failure({ error, refusal, at }:
  { error: string; refusal?: Spec | null; at?: string | null }) {
  if (refusal) return <RefusalCard refusal={refusal} at={at} />;
  return <p className="failure" role="alert">{error}</p>;
}
