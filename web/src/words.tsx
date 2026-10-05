// What the studio says things in, and how the agent's words are shown.
//
// The language somebody picked in the studio's bar ("Words in") holds for the
// whole page: the map, the panel beside it, the examples and the conversation
// all name a kind, a field or an example in that language where the module
// keeps its people's word for it, and in words made from its English name
// where it does not. One choice, read everywhere through `Language`.

import { createContext, useContext, useMemo } from "react";
import type { DraftState, ExampleResult } from "./api";
import { blocksOf, spoken, wordsOf } from "./studioMap";
import type { Piece } from "./studioMap";

export const Language = createContext<string>("en");

/** How things of this draft are called, in the language the page is read in. */
export function useSay(draft: DraftState | null) {
  const language = useContext(Language);
  const words = useMemo(() => (draft ? wordsOf(draft, language) : new Map<string, string>()),
    [draft, language]);
  return {
    language,
    words,
    /** A kind or a field by its people's word, otherwise in words. */
    name: (term: string) => words.get(term) ?? spoken(term),
    /** What an example says, in their words where it keeps them. */
    says: (example: ExampleResult) => example.labels?.[language] || example.says,
  };
}

function Pieces({ pieces }: { pieces: Piece[] }) {
  return (
    <>
      {pieces.map((piece, i) => piece.bold ? <strong key={i}>{piece.text}</strong>
        : piece.code ? <code key={i}>{piece.text}</code>
        : piece.italic ? <em key={i}>{piece.text}</em>
        : <span key={i}>{piece.text}</span>)}
    </>
  );
}

/** Something the agent said: its paragraphs, lists and bold as they are meant. */
export function Said({ text, className = "bubble-text" }: { text: string; className?: string }) {
  const blocks = useMemo(() => blocksOf(text), [text]);
  return (
    <div className={`said-text ${className}`}>
      {blocks.map((block, i) => block.kind === "paragraph" ? (
        <p key={i}>
          {block.lines.map((line, j) => (
            <span key={j}>{j > 0 && <br />}<Pieces pieces={line} /></span>
          ))}
        </p>
      ) : (
        <ul key={i} className="said-list">
          {block.items.map((item, j) => (
            <li key={j} className={item.depth ? "said-sub" : ""}>
              <span className="said-marker" aria-hidden="true">{item.marker}</span>
              <span><Pieces pieces={item.pieces} /></span>
            </li>
          ))}
        </ul>
      ))}
    </div>
  );
}
