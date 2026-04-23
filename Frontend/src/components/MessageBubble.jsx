export default function MessageBubble({ role, content }) {
  // For AI messages: split on "\n\n---\n" — main answer above, sources below
  const safeContent = content ?? '';
  let mainContent = safeContent;
  let sourcesContent = null;

  if (role === 'ai') {
    const separatorIdx = safeContent.indexOf('\n\n---\n');
    if (separatorIdx !== -1) {
      mainContent = safeContent.slice(0, separatorIdx);
      sourcesContent = safeContent.slice(separatorIdx + 6); // skip "\n\n---\n"
    }
  }

  return (
    <div className={`message-row ${role}`}>
      <div className={`message-bubble ${role}`}>
        <div className={`message-label ${role}`}>
          {role === 'human' ? 'You' : 'Jio AI'}
        </div>
        <div className="message-content">{mainContent}</div>
        {sourcesContent && (
          <div className="message-sources">{sourcesContent}</div>
        )}
      </div>
    </div>
  );
}
