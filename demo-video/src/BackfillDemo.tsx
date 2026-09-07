import type {CSSProperties, ReactNode} from 'react';
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const palette = {
  ink: '#10212b',
  muted: '#53646d',
  paper: '#f6f1e8',
  card: '#ffffff',
  accent: '#f2b84b',
  cool: '#dfeef2',
  green: '#dcebdc',
  red: '#f3dddd',
  line: '#c6d0d4',
};

const base: CSSProperties = {
  fontFamily: 'Arial, Helvetica, sans-serif',
  backgroundColor: palette.paper,
  color: palette.ink,
};

const titleStyle: CSSProperties = {
  fontSize: 72,
  lineHeight: 1.05,
  fontWeight: 800,
  letterSpacing: -2,
  margin: 0,
};

const eyebrowStyle: CSSProperties = {
  fontSize: 22,
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: 3,
  color: palette.muted,
  marginBottom: 18,
};

const captionStyle: CSSProperties = {
  position: 'absolute',
  left: 110,
  right: 110,
  bottom: 64,
  borderRadius: 22,
  backgroundColor: 'rgba(16, 33, 43, 0.94)',
  color: '#ffffff',
  padding: '22px 30px',
  fontSize: 31,
  lineHeight: 1.28,
  fontWeight: 650,
  textAlign: 'center',
};

const Card = ({children, style}: {children: ReactNode; style?: CSSProperties}) => (
  <div
    style={{
      backgroundColor: palette.card,
      border: `2px solid ${palette.line}`,
      borderRadius: 24,
      boxShadow: '0 16px 40px rgba(16, 33, 43, 0.08)',
      ...style,
    }}
  >
    {children}
  </div>
);

const FadeIn = ({children, delay = 0, style}: {children: ReactNode; delay?: number; style?: CSSProperties}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, [delay, delay + 18], [24, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return <div style={{opacity, transform: `translateY(${y}px)`, ...style}}>{children}</div>;
};

const ProblemScene = () => {
  const frame = useCurrentFrame();
  const slotPulse = interpolate(frame % 90, [0, 45, 89], [1, 1.05, 1]);
  const clients = ['C1', 'C2', 'C3', 'C4'];

  return (
    <AbsoluteFill style={{...base, padding: '90px 110px 150px'}}>
      <FadeIn>
        <div style={eyebrowStyle}>Backfill</div>
        <h1 style={titleStyle}>A cancellation creates a time-sensitive job.</h1>
      </FadeIn>

      <div style={{display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: 48, marginTop: 70}}>
        <FadeIn delay={12}>
          <Card style={{padding: 34}}>
            <div style={{fontSize: 26, fontWeight: 800, marginBottom: 22}}>Today’s appointment calendar</div>
            <div style={{display: 'grid', gridTemplateColumns: '150px 1fr', rowGap: 14, alignItems: 'center'}}>
              {['2:00 PM', '3:00 PM', '4:00 PM', '5:00 PM'].map((time, index) => (
                <div key={time} style={{display: 'contents'}}>
                  <div style={{fontSize: 24, color: palette.muted}}>{time}</div>
                  <div
                    style={{
                      height: 74,
                      borderRadius: 16,
                      border: `2px solid ${index === 2 ? '#d99999' : palette.line}`,
                      backgroundColor: index === 2 ? palette.red : palette.cool,
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0 24px',
                      fontSize: 25,
                      fontWeight: 700,
                      transform: index === 2 ? `scale(${slotPulse})` : undefined,
                    }}
                  >
                    {index === 2 ? 'Cancelled — slot now open' : 'Booked appointment'}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </FadeIn>

        <FadeIn delay={24}>
          <Card style={{padding: 34}}>
            <div style={{fontSize: 26, fontWeight: 800, marginBottom: 26}}>Eligible waitlist</div>
            <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>
              {clients.map((client, index) => (
                <div
                  key={client}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '18px 22px',
                    borderRadius: 16,
                    backgroundColor: index === 0 ? palette.green : '#f4f6f7',
                    border: `1px solid ${palette.line}`,
                  }}
                >
                  <span style={{fontSize: 25, fontWeight: 800}}>Candidate {client}</span>
                  <span style={{fontSize: 21, color: palette.muted}}>{index === 0 ? 'next eligible' : 'waiting'}</span>
                </div>
              ))}
            </div>
          </Card>
        </FadeIn>
      </div>

      <div style={captionStyle}>
        Backfill turns the interruption into a background workflow for appointment-based small businesses.
      </div>
    </AbsoluteFill>
  );
};

const ArchitectureScene = () => (
  <AbsoluteFill style={{...base, padding: '76px 100px 150px'}}>
    <FadeIn>
      <div style={eyebrowStyle}>Architecture</div>
      <h1 style={{...titleStyle, fontSize: 60}}>Agent orchestration, deterministic authority.</h1>
    </FadeIn>
    <FadeIn delay={12} style={{marginTop: 40, display: 'flex', justifyContent: 'center'}}>
      <Card style={{padding: 18, width: 1500, height: 690, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <Img src={staticFile('backfill-architecture.svg')} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
      </Card>
    </FadeIn>
    <div style={captionStyle}>
      Strands orchestrates bounded actions. Deterministic Backfill code owns eligibility, order, policy, idempotency, booking verification, terminal state, and recovered-value accounting.
    </div>
  </AbsoluteFill>
);

const EvidenceStep = ({
  start,
  title,
  detail,
  badge,
}: {
  start: number;
  title: string;
  detail: string;
  badge: string;
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [start, start + 16], [0.2, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(frame, [start, start + 16], [0.985, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <Card style={{padding: '20px 24px', opacity, transform: `scale(${scale})`}}>
      <div style={{display: 'flex', gap: 18, alignItems: 'flex-start'}}>
        <div
          style={{
            minWidth: 128,
            borderRadius: 999,
            backgroundColor: palette.cool,
            padding: '9px 14px',
            fontSize: 18,
            fontWeight: 800,
            textAlign: 'center',
          }}
        >
          {badge}
        </div>
        <div>
          <div style={{fontSize: 26, fontWeight: 850, marginBottom: 6}}>{title}</div>
          <div style={{fontSize: 21, lineHeight: 1.35, color: palette.muted}}>{detail}</div>
        </div>
      </div>
    </Card>
  );
};

const DemoScene = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{...base, padding: '70px 100px 155px'}}>
      <FadeIn>
        <div style={eyebrowStyle}>Verified provider run — August 26, 2026</div>
        <h1 style={{...titleStyle, fontSize: 57}}>The real recovery chain, replayed from preserved controlled evidence.</h1>
        <div style={{fontSize: 22, color: palette.muted, marginTop: 16}}>
          This is an evidence reconstruction of the verified run, not fabricated live footage.
        </div>
      </FadeIn>

      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginTop: 34}}>
        <EvidenceStep
          start={0.08 * fps}
          badge="1 · Gmail"
          title="One bounded offer sent"
          detail="Dedicated test slot: Aug 27, 4:00–4:30 PM ET. The message asked for exact first-line ACCEPT or DECLINE."
        />
        <EvidenceStep
          start={0.7 * fps}
          badge="2 · Reply"
          title="Recipient replied ACCEPT"
          detail="The consenting recipient’s preserved reply begins with the exact authoritative response: ACCEPT."
        />
        <EvidenceStep
          start={1.35 * fps}
          badge="3 · Calendar"
          title="Recovered booking verified"
          detail="The dedicated Backfill Demo calendar still contains “Backfill recovered test slot — C1” for the exact recovered slot."
        />
        <EvidenceStep
          start={2.0 * fps}
          badge="4 · Gmail"
          title="Confirmation sent"
          detail="The preserved confirmation states that Backfill booked and provider-verified the test appointment."
        />
        <EvidenceStep
          start={2.65 * fps}
          badge="5 · Runtime"
          title="COMPLETED_RECOVERED"
          detail="Verified terminal fact from the preserved run record. No synthetic terminal image is presented as original footage."
        />
        <EvidenceStep
          start={3.3 * fps}
          badge="$85 test"
          title="Recovered workflow value recorded"
          detail="Eighty-five dollars is test appointment value only — not project revenue and not a production customer claim."
        />
      </div>

      <div style={captionStyle}>
        Backfill waits for an authoritative response, verifies provider state after booking, sends confirmation, and only then records a recovered terminal state.
      </div>
    </AbsoluteFill>
  );
};

const CorrectnessScene = () => {
  const checks = [
    ['30 canonical tests', 'Public CI evidence'],
    ['STRANDS_SMOKE_OK', 'Zero-credential Strands smoke harness'],
    ['Deterministic IDs', 'Reconcile before retry'],
    ['Unexpected replies', 'Fail closed'],
    ['Policy exceptions', 'Interrupt for owner authority'],
    ['Checksum verification', 'Public repository integrity'],
  ];

  return (
    <AbsoluteFill style={{...base, padding: '82px 110px 155px'}}>
      <FadeIn>
        <div style={eyebrowStyle}>Why this is non-trivial</div>
        <h1 style={{...titleStyle, fontSize: 60}}>Correctness matters more than sending an email.</h1>
      </FadeIn>
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 22, marginTop: 62}}>
        {checks.map(([headline, detail], index) => (
          <FadeIn key={headline} delay={8 + index * 6}>
            <Card style={{padding: 28, minHeight: 155}}>
              <div style={{fontSize: 28, fontWeight: 850, marginBottom: 10}}>{headline}</div>
              <div style={{fontSize: 21, lineHeight: 1.35, color: palette.muted}}>{detail}</div>
            </Card>
          </FadeIn>
        ))}
      </div>
      <div style={{marginTop: 32, fontSize: 20, color: palette.muted}}>
        Public CI reference: run 33181027058 on main. The demo does not claim AgentCore or production deployment.
      </div>
      <div style={captionStyle}>
        Ambiguous Calendar or Gmail outcomes are reconciled before retry, reducing the risk of duplicate bookings or duplicate client contact.
      </div>
    </AbsoluteFill>
  );
};

const CloseScene = () => (
  <AbsoluteFill style={{...base, padding: '100px 125px 155px', justifyContent: 'center'}}>
    <FadeIn>
      <div style={eyebrowStyle}>Backfill · Professional Agents</div>
      <h1 style={{...titleStyle, fontSize: 78, maxWidth: 1450}}>
        Turn a cancellation from a small emergency into a background responsibility.
      </h1>
    </FadeIn>

    <FadeIn delay={16}>
      <div style={{display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 34, marginTop: 58}}>
        <Card style={{padding: 34}}>
          <div style={{fontSize: 27, fontWeight: 850, marginBottom: 18}}>What is verified</div>
          <div style={{fontSize: 24, lineHeight: 1.55}}>
            Consenting real-provider test-context recovery under the actual Backfill runtime, including provider-side booking verification and confirmation.
          </div>
        </Card>
        <Card style={{padding: 34}}>
          <div style={{fontSize: 27, fontWeight: 850, marginBottom: 18}}>Evidence boundaries</div>
          <div style={{fontSize: 22, lineHeight: 1.55, color: palette.muted}}>
            Not a production deployment. Not project revenue. The verified offer landed in Gmail Spam, so transactional deliverability remains a real pilot-readiness issue.
          </div>
        </Card>
      </div>
    </FadeIn>

    <FadeIn delay={32}>
      <div style={{marginTop: 42, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div style={{fontSize: 26, fontWeight: 800}}>github.com/84dnnvbdvp-debug/backfill</div>
        <div style={{fontSize: 25, color: palette.muted}}>MIT · architecture · setup · evidence boundaries · judge testing</div>
      </div>
    </FadeIn>

    <div style={captionStyle}>
      Routine recovery can progress end to end while consequential decisions remain bounded by explicit policy and human authority.
    </div>
  </AbsoluteFill>
);

export const BackfillDemo = () => {
  return (
    <AbsoluteFill style={base}>
      <Sequence from={0} durationInFrames={1050}>
        <ProblemScene />
      </Sequence>
      <Sequence from={1050} durationInFrames={900}>
        <ArchitectureScene />
      </Sequence>
      <Sequence from={1950} durationInFrames={3300}>
        <DemoScene />
      </Sequence>
      <Sequence from={5250} durationInFrames={1200}>
        <CorrectnessScene />
      </Sequence>
      <Sequence from={6450} durationInFrames={1200}>
        <CloseScene />
      </Sequence>
    </AbsoluteFill>
  );
};
