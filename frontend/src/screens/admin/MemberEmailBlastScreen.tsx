import { useMemberBlasts } from '@/api/memberBlast';
import { ContentContainer } from '@/screens/public/ContentContainer';

import { MemberBlastHistory } from './MemberBlastHistory';

export default function MemberEmailBlastScreen() {
  const blasts = useMemberBlasts();
  return (
    <ContentContainer>
      <h1 className="text-2xl font-medium tracking-tight">email blast</h1>
      <MemberBlastHistory blasts={blasts.data ?? []} />
    </ContentContainer>
  );
}
