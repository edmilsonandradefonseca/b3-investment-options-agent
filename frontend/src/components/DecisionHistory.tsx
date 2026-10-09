import PersonalHistory from './PersonalHistory';

type Obj = Record<string, unknown>;
const object = (value: unknown): Obj | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Obj : null;
const count = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? String(value) : 'Indisponível';

export default function DecisionHistory({ value }: { value: unknown }) {
  const context = object(value);
  const subjects = object(context?.subjects);
  const candidates = Array.isArray(context?.candidates) ? context.candidates.map(object).filter((item): item is Obj => item !== null) : [];
  if (!subjects || !candidates.length) return null;
  return <section className="analysis-section">
    <h4>Histórico por alternativa / contrato</h4>
    <p className="muted">Correspondência pelo símbolo exato. Execuções observadas não comprovam uma estratégia comparável. O histórico não altera o ranking.</p>
    <div className="table-wrap"><table><thead><tr>
      <th>Ativo / contrato</th><th>Ação atual</th><th>Execuções observadas</th><th>Sequências observadas</th><th>Outcomes elegíveis</th><th>Confiança de similaridade</th>
    </tr></thead><tbody>{candidates.map((candidate, index) => {
      const subject = String(candidate.history_subject ?? '');
      const history = object(subjects[subject]);
      const admission = object(history?.historical_admission);
      return <tr key={`${String(candidate.candidate_id)}:${index}`} title={String(candidate.candidate_id)}>
        <td>{subject}</td><td>{String(candidate.action ?? 'ANALYZE')}</td>
        <td>{count(history?.execution_count)}</td><td>{count(history?.observed_sequence_count)}</td>
        <td>{count(admission?.eligible_outcome_count)}</td><td>{count(admission?.similarity_confidence)}</td>
      </tr>;
    })}</tbody></table></div>
    <p className="muted">Resultado final, IV/regime de entrada e evidências de exercício, vencimento e rolagem continuam necessários. Learnings favoráveis e contrários: indisponíveis nesta projeção de execuções. Amostra elegível zero não significa ausência de perdas ou exercício.</p>
    {Object.entries(subjects).map(([subject, history]) => <details key={subject}>
      <summary>{subject} — fontes, movimentos, corte temporal e limitações</summary>
      <PersonalHistory value={history} />
    </details>)}
    {typeof context?.candidate_details_omitted === 'number' && context.candidate_details_omitted > 0 && <p className="muted">Candidatos adicionais omitidos: {context.candidate_details_omitted}.</p>}
  </section>;
}
