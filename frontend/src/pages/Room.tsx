const Room = () => {
  const players = [
    { id: 'p1', name: 'Player 1', chips: 500, active: false },
    { id: 'p2', name: 'Player 2', chips: 300, active: true },
    { id: 'p3', name: 'Player 3', chips: 240, active: false },
  ]

  return (
    <div className="app room-shell">
      <div className="sparkle-field" aria-hidden="true">
        <span className="sparkle s1" />
        <span className="sparkle s2" />
        <span className="sparkle s3" />
        <span className="sparkle s4" />
        <span className="sparkle s5" />
        <span className="sparkle s6" />
      </div>

      <header className="room-header">
        <p className="room-title">TIEN LEN</p>
        <p className="room-subtitle">Room 9XK3 • 3/4 players</p>
      </header>

      <section className="room-players">
        {players.map((player) => (
          <article
            key={player.id}
            className={`room-player${player.active ? ' active' : ''}`}
          >
            <div className="room-avatar">{player.name.slice(0, 1)}</div>
            <div>
              <p className="room-player-name">{player.name}</p>
              <p className="room-player-chip">{player.chips} coins</p>
            </div>
            {player.active ? <span className="room-player-pill">Turn</span> : null}
          </article>
        ))}
      </section>

      <section className="room-table">
        <div className="room-table-score">
          <span className="room-score-chip">500</span>
          <span className="room-score-chip">300</span>
        </div>
        <div className="room-trick">
          <div className="room-card">
            <span>7</span>
            <span className="room-card-suit club">&clubs;</span>
          </div>
          <div className="room-card">
            <span>7</span>
            <span className="room-card-suit heart">&hearts;</span>
          </div>
        </div>
      </section>

      <section className="room-hand">
        <div className="room-hand-cards">
          {[
            { value: '10', suit: 'spade' },
            { value: '10', suit: 'diamond' },
            { value: '9', suit: 'spade' },
            { value: '8', suit: 'heart' },
            { value: '8', suit: 'diamond' },
            { value: '3', suit: 'club' },
          ].map((card, index) => (
            <div
              key={`${card.value}-${card.suit}`}
              className={`room-card small ${index === 3 ? 'selected' : ''}`}
            >
              <span>{card.value}</span>
              <span className={`room-card-suit ${card.suit}`}>
                {card.suit === 'spade' && <span>&spades;</span>}
                {card.suit === 'diamond' && <span>&diams;</span>}
                {card.suit === 'heart' && <span>&hearts;</span>}
                {card.suit === 'club' && <span>&clubs;</span>}
              </span>
            </div>
          ))}
        </div>
        <button className="room-action subtle" type="button">
          XEP BAI
        </button>
      </section>

      <section className="room-actions">
        <button className="room-action ghost" type="button">
          BO LUOT
        </button>
        <button className="room-action primary" type="button">
          DANH
        </button>
      </section>
    </div>
  )
}

export default Room
