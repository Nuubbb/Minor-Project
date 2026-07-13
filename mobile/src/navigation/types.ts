export type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Live: undefined;
  History: undefined;
  Community: undefined;
  Map: undefined;
  Events: undefined;
  Users: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Tabs: undefined;
  AlertValidator: { alertId: number };
  PeerReportValidator: { reportId: number };
  MemberCamera: { memberId: number; memberName: string };
};
