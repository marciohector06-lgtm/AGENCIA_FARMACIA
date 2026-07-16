import { ProdutoSugeridoCard } from "@/components/atendimento/ProdutoSugeridoCard";
import { ChatMessage } from "@/lib/useAtendimentoChat";
import { ProdutoSugerido } from "@/lib/types";

export function ChatBubble({
  msg,
  onConfirmar,
  disabled,
}: {
  msg: ChatMessage;
  onConfirmar: (produto: ProdutoSugerido, quantidade: number) => void;
  disabled: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-lg rounded-lg px-4 py-2 text-sm ${
          isUser ? "bg-red-600 text-white" : "bg-slate-100 text-slate-700"
        }`}
      >
        {msg.text}
      </div>
      {/* CLIN-06: disclaimer sempre em destaque visual separado — nunca dentro
          do balão de resposta, pra não se misturar com o texto do "avatar". */}
      {!isUser && msg.disclaimer && (
        <div className="mt-1 max-w-lg rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700">
          {msg.disclaimer}
        </div>
      )}
      {msg.vendaId && <p className="mt-1 text-xs text-red-600">Venda registrada: {msg.vendaId}</p>}
      {msg.produtos && msg.produtos.length > 0 && (
        <div className="mt-2 flex flex-col gap-2">
          {msg.produtos.map((p) => (
            <ProdutoSugeridoCard key={p.produto_id} produto={p} disabled={disabled} onConfirmar={onConfirmar} />
          ))}
        </div>
      )}
    </div>
  );
}
